"""Rule-based job/resume intelligence layer for the local matching pipeline.

This module implements the recruiter-style logic that sits on top of the raw
embedding similarity score computed by the sentence-transformer model:

- Role classification (DevOps/SRE/Platform vs Data/ML/Frontend/... )
- Weighted critical-skill taxonomy (Kubernetes/Terraform/AWS/... > generic words)
- Mandatory hard filters (non-Europe, intern/junior, wrong specialization/language)
- A structured resume profile (years of experience, roles, skill categories)
- A transparent weighted scoring formula with penalties and an explanation

Everything here is deterministic and keyword/regex based so it works without
any network calls and is cheap enough to run on every job on every pipeline
run. Only the final Ollama reasoning step (unchanged) uses the local LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Critical skill taxonomy (weighted). Higher weight = more important signal.
# ---------------------------------------------------------------------------
CRITICAL_SKILLS: dict[str, float] = {
    # Container / orchestration
    "kubernetes": 3.0, "k8s": 3.0, "helm": 2.0, "docker": 2.5, "eks": 2.5,
    "ecs": 2.0, "openshift": 2.0, "argo cd": 2.0, "argocd": 2.0, "flux": 1.5,
    # IaC
    "terraform": 3.0, "pulumi": 2.0, "cloudformation": 1.8, "ansible": 2.0,
    "packer": 1.2, "crossplane": 1.5,
    # Cloud
    "aws": 3.0, "azure": 2.5, "gcp": 2.5, "iam": 1.8, "vpc": 1.5,
    # CI/CD
    "jenkins": 1.8, "github actions": 2.0, "gitlab ci": 2.0, "circleci": 1.5,
    "ci/cd": 1.8,
    # Observability
    "prometheus": 2.2, "grafana": 2.2, "datadog": 1.8, "elk": 1.5,
    "opensearch": 1.5, "elasticsearch": 1.5, "observability": 1.8,
    "opentelemetry": 1.8, "newrelic": 1.2,
    # Networking / OS
    "linux": 2.5, "networking": 1.8, "dns": 1.2, "load balancing": 1.2,
    "nginx": 1.2, "shell": 1.5, "bash": 1.5,
    # Data stores commonly used by platform teams
    "postgresql": 1.5, "postgres": 1.5, "mysql": 1.0, "redis": 1.5,
    "clickhouse": 1.5, "kafka": 1.8, "rabbitmq": 1.2,
    # Languages
    "python": 2.0, "go": 1.8, "golang": 1.8, "typescript": 0.8,
    # Security
    "devsecops": 1.5, "vault": 1.5, "sso": 1.0, "oauth": 1.0,
}

GENERIC_SKILL_WEIGHT = 0.5

# ---------------------------------------------------------------------------
# Role taxonomy
# ---------------------------------------------------------------------------
PRIMARY_ROLE_KEYWORDS: dict[str, list[str]] = {
    "Senior DevOps Engineer": ["senior devops", "devops engineer", "devops"],
    "Platform Engineer": ["platform engineer", "platform team", "internal platform"],
    "Cloud Engineer": ["cloud engineer", "cloud infrastructure"],
    "Infrastructure Engineer": ["infrastructure engineer", "infrastructure team"],
    "Site Reliability Engineer": ["site reliability", "sre engineer", " sre", "sre "],
    "Platform SRE": ["platform sre"],
    "Cloud Platform Engineer": ["cloud platform engineer"],
    "DevSecOps Engineer": ["devsecops"],
    "Observability Engineer": ["observability engineer", "monitoring engineer"],
    "Kubernetes Engineer": ["kubernetes engineer"],
    "Infrastructure Automation Engineer": ["infrastructure automation"],
    "Production Engineer": ["production engineer"],
    "Systems Engineer": ["systems engineer"],
    "Platform Operations Engineer": ["platform operations"],
}

SECONDARY_ROLE_KEYWORDS: dict[str, list[str]] = {
    "Backend Infrastructure": ["backend infrastructure"],
    "Cloud Security": ["cloud security engineer", "security engineer"],
    "Release Engineer": ["release engineer"],
    "Build Engineer": ["build engineer"],
    "Technical Operations": ["technical operations", "techops"],
    "Engineering Productivity": ["engineering productivity", "developer productivity"],
    "Developer Experience": ["developer experience", "devex"],
}

LOW_PRIORITY_ROLE_KEYWORDS: dict[str, list[str]] = {
    "Data Engineer": ["data engineer"],
    "Data Platform Engineer": ["data platform engineer"],
    "Analytics Engineer": ["analytics engineer"],
    "Machine Learning Engineer": ["machine learning engineer", "ml engineer"],
    "AI Engineer": ["ai engineer"],
    "Frontend Engineer": ["frontend engineer", "front-end engineer", "front end engineer"],
    "Mobile Engineer": ["mobile engineer", "ios engineer", "android engineer"],
    "Full Stack Engineer": ["full stack", "fullstack"],
    "Java Backend Engineer": ["java engineer", "java developer", "java backend"],
    "PHP Engineer": ["php engineer", "php developer"],
    ".NET Engineer": [".net engineer", ".net developer", "dotnet"],
    "QA Engineer": ["qa engineer", "quality assurance", "test engineer", "sdet"],
    "Business Analyst": ["business analyst"],
    "Product Manager": ["product manager"],
    "Designer": ["ux designer", "ui designer", "product designer"],
}

# Score contribution per priority tier (feeds "role relevance" component, 0-100)
ROLE_PRIORITY_SCORE = {
    "primary": 100.0,
    "secondary": 60.0,
    "low": 20.0,
    "unknown": 45.0,
}

# Extra flat penalty applied to the final score for specific low-priority /
# disqualifying categories, per the recruiter brief.
ROLE_PENALTIES: dict[str, float] = {
    "Machine Learning Engineer": 40.0,
    "AI Engineer": 40.0,
    "Data Engineer": 20.0,
    "Data Platform Engineer": 20.0,
    "Analytics Engineer": 20.0,
    "Frontend Engineer": 60.0,
    "Mobile Engineer": 50.0,
    "Full Stack Engineer": 25.0,
    "Java Backend Engineer": 40.0,
    "PHP Engineer": 45.0,
    ".NET Engineer": 40.0,
    "QA Engineer": 35.0,
    "Business Analyst": 55.0,
    "Product Manager": 55.0,
    "Designer": 60.0,
}

# ---------------------------------------------------------------------------
# Mandatory hard-reject filters
# ---------------------------------------------------------------------------
JUNIOR_INTERN_PATTERNS = re.compile(
    r"\b(intern|internship|working student|graduate program|trainee|junior|entry[- ]level|new grad)\b",
    re.IGNORECASE,
)

# language-only roles: title strongly implies this language is the core stack.
LANGUAGE_ONLY_PATTERNS: dict[str, re.Pattern] = {
    "java": re.compile(r"\bjava\s+(developer|engineer|backend)\b", re.IGNORECASE),
    "scala": re.compile(r"\bscala\s+(developer|engineer)\b", re.IGNORECASE),
    "rust": re.compile(r"\brust\s+(developer|engineer)\b", re.IGNORECASE),
    "go": re.compile(r"\bgo(lang)?\s+(developer|engineer)\b", re.IGNORECASE),
    ".net": re.compile(r"\b(\.net|dotnet)\s+(developer|engineer)\b", re.IGNORECASE),
    "php": re.compile(r"\bphp\s+(developer|engineer)\b", re.IGNORECASE),
}

HARD_REJECT_TECH_PATTERNS: dict[str, re.Pattern] = {
    "sap": re.compile(r"\bsap\b", re.IGNORECASE),
    "salesforce": re.compile(r"\bsalesforce\b", re.IGNORECASE),
    "embedded": re.compile(r"\bembedded (systems|software)\b", re.IGNORECASE),
    "fpga": re.compile(r"\bfpga\b", re.IGNORECASE),
    "asic": re.compile(r"\basic\b", re.IGNORECASE),
}

VISA_KEYWORDS = re.compile(
    r"\b(visa|sponsorship|relocation|work permit|international applicants|blue card)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Company quality tiers (small positive signal only)
# ---------------------------------------------------------------------------
TOP_TIER_COMPANIES = {
    "datadog", "cloudflare", "elastic", "grafana labs", "docker", "canonical",
    "gitlab", "hashicorp", "red hat", "spotify", "booking.com", "adyen",
    "wise", "stripe", "atlassian", "confluent", "snowflake", "mongodb",
    "n26", "celonis", "miro", "asml", "sap", "bosch", "siemens", "nvidia",
    "github", "amazon", "microsoft", "google",
}

# ---------------------------------------------------------------------------
# Scoring weights (spec-defined)
# ---------------------------------------------------------------------------
WEIGHT_EMBEDDING = 0.30
WEIGHT_ROLE = 0.25
WEIGHT_REQUIRED_SKILLS = 0.20
WEIGHT_PREFERRED_SKILLS = 0.10
WEIGHT_VISA = 0.05
WEIGHT_COMPANY = 0.05
WEIGHT_LOCATION = 0.05

SHOULD_APPLY_THRESHOLD = 70.0


def _normalize(text: str | None) -> str:
    return (text or "").lower()


def extract_skills(text: str | None) -> set[str]:
    """Return the set of known critical skills mentioned in a text blob."""
    t = _normalize(text)
    found = set()
    for skill in CRITICAL_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, t):
            found.add(skill)
    return found


def classify_role(title: str | None, description: str | None = None) -> tuple[str, str]:
    """Classify a job (or resume headline) into (category, priority).

    priority is one of "primary", "secondary", "low", "unknown".
    """
    text = _normalize(f"{title or ''} {description[:500] if description else ''}")
    title_only = _normalize(title)

    for category, keywords in PRIMARY_ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw.strip() in title_only:
                return category, "primary"
    for category, keywords in SECONDARY_ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw in title_only:
                return category, "secondary"
    for category, keywords in LOW_PRIORITY_ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw in title_only:
                return category, "low"

    # Fall back to scanning the description if the title didn't match anything.
    for category, keywords in PRIMARY_ROLE_KEYWORDS.items():
        for kw in keywords:
            if kw.strip() in text:
                return category, "primary"

    return "Other", "unknown"


# Job-specific location text is more reliable than the job's `country_id`,
# because crawled jobs are sometimes tagged with their company's HQ country
# rather than the actual office/region the posting is for (e.g. a Bangalore
# role at a Germany-HQ'd company). So we check location text FIRST.
NON_EUROPE_LOCATION_MARKERS = [
    "united states", "usa", "us", "canada", "india",
    "bangalore", "bengaluru", "hyderabad", "mumbai", "delhi", "pune",
    "chennai", "gurugram", "gurgaon", "noida",
    "singapore", "australia", "sydney", "melbourne", "brisbane",
    "brazil", "sao paulo", "mexico", "china", "beijing",
    "shanghai", "shenzhen", "japan", "tokyo", "seoul", "korea",
    "dubai", "abu dhabi", "uae", "tel aviv", "israel",
    "san francisco", "seattle", "new york", "toronto", "vancouver",
    "austin", "boston", "chicago", "denver", "atlanta", "los angeles",
    "amer",
]

EUROPE_LOCATION_MARKERS = [
    "germany", "berlin", "munich", "hamburg", "frankfurt", "cologne",
    "france", "paris", "nantes", "lyon", "toulouse",
    "netherlands", "amsterdam", "rotterdam", "the hague", "utrecht",
    "ireland", "dublin", "cork",
    "spain", "madrid", "barcelona", "valencia",
    "portugal", "lisbon", "porto",
    "poland", "warsaw", "warszawa", "krakow", "wroclaw",
    "czech", "prague", "austria", "vienna",
    "switzerland", "zurich", "geneva", "basel",
    "sweden", "stockholm", "gothenburg",
    "norway", "oslo", "denmark", "copenhagen", "finland", "helsinki",
    "belgium", "brussels", "antwerp",
    "italy", "milan", "rome", "turin",
    "greece", "athens", "romania", "bucharest",
    "hungary", "budapest", "united kingdom", "uk", "london", "manchester",
    "edinburgh", "europe", "emea",
]


def _matches_any(text: str, markers: list[str]) -> bool:
    for marker in markers:
        pattern = r"\b" + re.escape(marker.strip()) + r"\b"
        if re.search(pattern, text):
            return True
    return False


def is_europe_location(location: str | None, country_name: str | None, country_is_eu: bool | None) -> bool:
    loc = _normalize(location or "")

    # If a European option is explicitly listed (common for multi-region
    # remote postings like "Remote, UK; Remote, US"), treat it as reachable.
    if _matches_any(loc, EUROPE_LOCATION_MARKERS):
        return True
    if _matches_any(loc, NON_EUROPE_LOCATION_MARKERS):
        return False

    # Location text was ambiguous/empty; fall back to the job's country record.
    if country_is_eu is not None:
        return bool(country_is_eu)

    # No usable signal at all: don't hard-reject.
    return True


@dataclass
class MandatoryFilterResult:
    rejected: bool
    reason: str | None = None


def mandatory_filter(
    title: str,
    description: str | None,
    location: str | None,
    country_name: str | None,
    country_is_eu: bool | None,
    resume_skills: set[str],
) -> MandatoryFilterResult:
    """Hard reject rules evaluated BEFORE any scoring/embedding cost."""
    text = f"{title} {description or ''}"

    # Relaxed location filter: keep remote/distributed roles and allow global
    # applications; only hard-reject if the posting is explicitly non-remote
    # and outside any known region.
    loc = _normalize(location or "")
    is_remote = any(k in loc for k in ["remote", "distributed", "work from home", "wfh"])
    if not is_remote and not is_europe_location(location, country_name, country_is_eu):
        return MandatoryFilterResult(True, "Location outside Europe")

    if JUNIOR_INTERN_PATTERNS.search(title):
        return MandatoryFilterResult(True, "Internship / graduate / junior position")

    for lang, pattern in LANGUAGE_ONLY_PATTERNS.items():
        if pattern.search(title) and lang not in resume_skills and lang.rstrip(".") not in resume_skills:
            return MandatoryFilterResult(True, f"Requires {lang}-only specialization not present in resume")

    for tech, pattern in HARD_REJECT_TECH_PATTERNS.items():
        if pattern.search(title) and tech not in resume_skills:
            return MandatoryFilterResult(True, f"Requires {tech.upper()} specialization not present in resume")

    return MandatoryFilterResult(False, None)


_REQUIREMENTS_HEADERS = re.compile(
    r"(requirements|what you.?ll need|must have|qualifications|you have)", re.IGNORECASE
)
_PREFERRED_HEADERS = re.compile(
    r"(nice to have|preferred|bonus points|good to have|pluses?)", re.IGNORECASE
)


def split_required_preferred(description: str | None) -> tuple[set[str], set[str]]:
    """Best-effort split of a JD into required vs preferred skill mentions."""
    text = description or ""
    if not text:
        return set(), set()

    req_match = _REQUIREMENTS_HEADERS.search(text)
    pref_match = _PREFERRED_HEADERS.search(text)

    if req_match and pref_match and pref_match.start() > req_match.start():
        required_block = text[req_match.start():pref_match.start()]
        preferred_block = text[pref_match.start():]
    elif pref_match:
        preferred_block = text[pref_match.start():]
        required_block = text[: pref_match.start()]
    else:
        required_block = text
        preferred_block = ""

    required_skills = extract_skills(required_block)
    preferred_skills = extract_skills(preferred_block) - required_skills
    return required_skills, preferred_skills


_YEARS_PATTERN = re.compile(r"(\d+)\s*\+?\s*years?", re.IGNORECASE)
_CERT_PATTERN = re.compile(
    r"\b(aws certified|azure certified|ckad|cka|cks|terraform associate|gcp certified|comptia)\b",
    re.IGNORECASE,
)


def build_resume_profile(resume_text: str | None) -> dict:
    """Extract a structured profile from raw resume text (cheap, deterministic)."""
    text = resume_text or ""
    skills = extract_skills(text)

    years_matches = [int(m.group(1)) for m in _YEARS_PATTERN.finditer(text)]
    years_experience = max(years_matches) if years_matches else None

    cloud_providers = sorted(skills & {"aws", "azure", "gcp"})
    cicd = sorted(skills & {"jenkins", "github actions", "gitlab ci", "circleci", "ci/cd"})
    containers = sorted(skills & {"kubernetes", "k8s", "docker", "helm", "eks", "ecs", "openshift"})
    iac = sorted(skills & {"terraform", "pulumi", "cloudformation", "ansible", "packer", "crossplane"})
    monitoring = sorted(skills & {"prometheus", "grafana", "datadog", "elk", "opensearch", "elasticsearch", "observability", "opentelemetry", "newrelic"})
    languages = sorted(skills & {"python", "go", "golang", "typescript", "bash", "shell", "java", "scala", "rust", "php"})
    certifications = sorted(set(m.group(0) for m in _CERT_PATTERN.finditer(text)))

    category, priority = classify_role(text[:400], text)

    return {
        "skills": sorted(skills),
        "years_experience": years_experience,
        "cloud_providers": cloud_providers,
        "cicd": cicd,
        "containers": containers,
        "iac": iac,
        "monitoring": monitoring,
        "languages": languages,
        "certifications": certifications,
        "primary_role_guess": category,
        "primary_role_priority": priority,
    }


def company_quality_score(company_name: str | None) -> float:
    if not company_name:
        return 50.0
    return 100.0 if _normalize(company_name) in TOP_TIER_COMPANIES else 50.0


@dataclass
class ScoreResult:
    overall: float
    role_category: str
    role_priority: str
    breakdown: dict = field(default_factory=dict)
    required_skills_missing: list[str] = field(default_factory=list)
    should_apply: bool = False


def compute_weighted_score(
    *,
    embedding_score_0_100: float,
    job_title: str,
    job_description: str | None,
    location: str | None,
    company_name: str | None,
    visa_sponsorship: str | None,
    workplace_type: str | None,
    resume_skills: set[str],
    resume_profile: dict,
) -> ScoreResult:
    role_category, role_priority = classify_role(job_title, job_description)
    role_score = ROLE_PRIORITY_SCORE.get(role_priority, 45.0)

    required_skills, preferred_skills = split_required_preferred(job_description)
    if required_skills:
        matched_required = required_skills & resume_skills
        required_pct = (len(matched_required) / len(required_skills)) * 100.0
        missing_required = sorted(required_skills - resume_skills)
    else:
        required_pct = 65.0  # neutral when JD has no clearly parsed requirements
        missing_required = []

    if preferred_skills:
        matched_preferred = preferred_skills & resume_skills
        preferred_pct = (len(matched_preferred) / len(preferred_skills)) * 100.0
    else:
        preferred_pct = 65.0

    visa_score = 100.0 if (
        (visa_sponsorship or "").lower() in ("yes", "likely")
        or VISA_KEYWORDS.search(job_description or "")
    ) else 40.0

    company_score = company_quality_score(company_name)

    location_score = 100.0 if (workplace_type or "").lower() in ("remote", "hybrid") else 70.0

    base = (
        embedding_score_0_100 * WEIGHT_EMBEDDING
        + role_score * WEIGHT_ROLE
        + required_pct * WEIGHT_REQUIRED_SKILLS
        + preferred_pct * WEIGHT_PREFERRED_SKILLS
        + visa_score * WEIGHT_VISA
        + company_score * WEIGHT_COMPANY
        + location_score * WEIGHT_LOCATION
    )

    penalty = ROLE_PENALTIES.get(role_category, 0.0)

    # Missing-critical-skill penalties, weighted by the skill's importance.
    skill_penalty = 0.0
    for skill in missing_required:
        weight = CRITICAL_SKILLS.get(skill, GENERIC_SKILL_WEIGHT)
        skill_penalty += min(15.0, weight * 5.0)
    skill_penalty = min(skill_penalty, 40.0)

    # Experience gap penalty.
    experience_penalty = 0.0
    required_years = None
    if job_description:
        years_matches = [int(m.group(1)) for m in _YEARS_PATTERN.finditer(job_description)]
        if years_matches:
            required_years = max(years_matches)
    resume_years = resume_profile.get("years_experience")
    if required_years and resume_years is not None and required_years - resume_years > 3:
        experience_penalty = 15.0

    overall = max(0.0, min(100.0, base - penalty - skill_penalty - experience_penalty))

    breakdown = {
        "embedding_similarity": round(embedding_score_0_100, 1),
        "role_relevance": round(role_score, 1),
        "required_skill_match": round(required_pct, 1),
        "preferred_skill_match": round(preferred_pct, 1),
        "visa_score": round(visa_score, 1),
        "company_quality": round(company_score, 1),
        "location_score": round(location_score, 1),
        "role_penalty": round(penalty, 1),
        "missing_skill_penalty": round(skill_penalty, 1),
        "experience_gap_penalty": round(experience_penalty, 1),
    }

    return ScoreResult(
        overall=round(overall, 2),
        breakdown=breakdown,
        role_category=role_category,
        role_priority=role_priority,
        required_skills_missing=missing_required,
        should_apply=overall >= SHOULD_APPLY_THRESHOLD,
    )
