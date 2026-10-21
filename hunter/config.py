"""Everything you are likely to tune lives here.

The hunter targets New Zealand roles that can carry an India Skilled Work Visa:
the job must be full time (30h+/week) with an AEWV-accredited employer, and the
employer must be willing to describe it as Software Engineer / Software and
Applications Programmer / ICT Project Manager.
"""

import re

# --- What to search for -----------------------------------------------------

# Seek does full-text matching, so each term is a separate query.
SEEK_KEYWORDS = [
    "devops",
    "site reliability",
    "sre",
    "platform engineer",
    "cloud engineer",
    "cloud architect",
    "infrastructure engineer",
    "devsecops",
    "kubernetes",
    "terraform",
    "aws engineer",
    "azure engineer",
    "mlops",
    "forward deployed",
    "observability",
    "ai platform",
    "ai infrastructure",
]

# LinkedIn's guest search rate-limits hard, so terms are OR-ed into a few queries.
LINKEDIN_QUERIES = [
    'devops OR "site reliability" OR SRE OR devsecops',
    '"platform engineer" OR "cloud engineer" OR "infrastructure engineer" OR "cloud architect"',
    'kubernetes OR terraform OR mlops OR observability',
    '"forward deployed" OR "solutions engineer" OR "deployment engineer"',
    '"AI platform" OR "ML platform" OR "AI infrastructure" OR llmops OR "AI engineer"',
]

# A job is kept only if its title matches one of these.
CORE_TITLE = re.compile(
    r"dev\s?ops|devsecops|\bsre\b|site reliability|reliability engineer|"
    r"platform (engineer|engineering|specialist|lead|architect)|developer platform|"
    r"cloud (engineer|architect|ops|operations|platform|infrastructure|specialist|consultant|lead|security)|"
    r"infrastructure (engineer|lead|architect|specialist)|kubernetes|\bk8s\b|"
    r"forward[- ]deployed|mlops|llmops|observability|build (and|&) release|release engineer|"
    r"(ai|ml|llm) (platform|infrastructure|infra|ops|operations|reliability)|agents? engineer|"
    r"\b(aws|azure|gcp)\b.*(engineer|architect|specialist|consultant)",
    re.I,
)
# Weaker matches: shown, but ranked lower.
ADJACENT_TITLE = re.compile(
    r"systems engineer|linux|automation engineer|integration engineer|solutions engineer|"
    r"deployment engineer|production engineer|technical operations|cloud|\bai engineer|"
    r"machine learning engineer",
    re.I,
)
# Dropped even if the title otherwise matches.
EXCLUDE_TITLE = re.compile(
    r"\bintern(ship)?\b|graduate|\bgrad\b|junior|apprentice|"
    r"sales|account (manager|executive)|business development|recruit|"
    r"electrical|mechanical|civil|plumb|hvac|fire|security officer|"
    r"\btest(er|ing)? analyst\b|teacher|nurse|itsm|servicenow|product (manager|owner)|"
    r"mandarin|japanese|korean speaking|help ?desk|service desk|desktop support",
    re.I,
)

# --- Visa fit ---------------------------------------------------------------

# Hard stops: the ad rules out anyone who needs a visa. Shown on the site, never emailed.
HARD_BLOCKERS = [
    (r"(no|not|unable to|cannot|can't|won't|will not|don't|do not|isn't|is not)\s+(be\s+)?(able\s+to\s+)?"
     r"(offer\w*|provid\w*|support\w*|consider\w*|available\s+for)?\s*(any\s+)?(visa\s+)?sponsor",
     "Says no visa sponsorship"),
    (r"without\s+(the\s+need\s+for\s+)?(visa\s+)?sponsorship", "Says no visa sponsorship"),
    (r"sponsorship\s+(is\s+)?(not|un)\s*available", "Says no visa sponsorship"),
    (r"(citizens?|residents?)\s+only", "NZ citizens/residents only"),
    (r"(must|need to|required to)\s+be\s+(an?\s+)?(nz|new zealand)\s+(citizen|resident)", "NZ citizens/residents only"),
    (r"(permanent\s+residen\w+|residency|citizenship)\s+(is\s+)?(required|essential|mandatory)", "NZ citizens/residents only"),
    (r"security\s+clearance", "Needs NZ security clearance (usually citizens)"),
]

# Soft warnings: common boilerplate that a strong candidate can still push past.
SOFT_BLOCKERS = [
    (r"(must|need to|needs to|required to|should|will need to)\s+(already\s+)?(have|hold|possess)\s+(the\s+)?"
     r"(full\s+|valid\s+|current\s+|unrestricted\s+|existing\s+)?(legal\s+)?(right|rights|eligibility|entitlement)\s+to\s+work",
     "Asks for existing right to work"),
    (r"(work|working)\s+rights\s+(in\s+(nz|new zealand)\s+)?(is\s+|are\s+)?(required|essential|mandatory|needed)",
     "Asks for NZ work rights"),
    (r"(only|we can only)\s+consider\s+(applicants|candidates)\s+(with|who)", "Limits who they consider"),
    (r"(must|currently|already)\s+(be\s+)?(based|located|living|residing)\s+in\s+(nz|new zealand|auckland|wellington|christchurch)",
     "Wants candidates already in NZ"),
]

POSITIVES = [
    (r"visa\s+sponsorship\s+(is\s+)?(available|offered|provided|possible|considered)", "Offers visa sponsorship"),
    (r"(we|will|can|happy to|able to)\s+(can\s+)?sponsor", "Offers visa sponsorship"),
    (r"relocation\s+(support|assistance|package|allowance|help)", "Relocation support"),
    (r"accredited\s+employer", "Mentions accredited employer"),
    (r"(overseas|international)\s+(applicants|candidates|talent)\s+(are\s+)?(welcome|encouraged|considered)",
     "Welcomes overseas applicants"),
    (r"open\s+to\s+(overseas|international)", "Welcomes overseas applicants"),
]

# Advertisers that are agencies: the real employer is hidden, so its
# accreditation has to be asked about.
RECRUITERS = re.compile(
    r"recruit|talent|staffing|personnel|search partners|\bhays\b|robert walters|robert half|randstad|"
    r"absolute it|potentia|momentum consulting|halcyon knights|hudson|michael page|"
    r"davidson|madison|adecco|younity|sourced it|harvey nash|workforce|placeme|tribe group|"
    r"presto resourcing|crescent consulting|\bresourcing\b|"
    r"jobs?\s+(nz|limited|ltd)",
    re.I,
)

# Ad names that do not match the INZ legal name. Key: lowercased ad name.
EMPLOYER_ALIASES = {
    "bnz": "Bank of New Zealand",
    "asb": "ASB Bank",
    "asb bank": "ASB Bank",
    "anz": "ANZ Bank New Zealand",
    "anz new zealand": "ANZ Bank New Zealand",
    "westpac": "Westpac New Zealand",
    "westpac nz": "Westpac New Zealand",
    "spark": "Spark New Zealand",
    "spark nz": "Spark New Zealand",
    "one nz": "One New Zealand",
    "2degrees": "Two Degrees",
    "nzx": "NZX Limited",
    "fonterra": "Fonterra Co-operative",
    "air new zealand": "Air New Zealand",
    "trade me": "Trade Me",
    "xero": "Xero",
}

# --- Your profile (from hire-abhishek.vercel.app) ---------------------------

# Senior Platform & SRE engineer, 5+ years (Octro, Gameskraft, Paytm, MediBuddy).
# Edge: AI operations agents in production (MCP, LLM evals, vLLM on EKS),
# AWS cost cuts, Terraform/GitOps platforms. AI-infra and FDE roles suit this well.
# Each skill found in an ad adds to its score.
SKILLS = {
    "aws": r"\baws\b|amazon web services",
    "kubernetes": r"kubernetes|\bk8s\b|\beks\b",
    "terraform": r"terraform",
    "ecs": r"\becs\b|fargate",
    "docker": r"docker|container",
    "helm": r"\bhelm\b",
    "argocd": r"argo\s?cd|gitops",
    "jenkins": r"jenkins|codepipeline|github actions|gitlab ci|ci/cd|cicd",
    "observability": r"opentelemetry|prometheus|grafana|observability|\belk\b|opensearch|new relic|datadog",
    "python": r"\bpython\b",
    "bash": r"\bbash\b|shell script",
    "ansible": r"ansible",
    "security": r"\bvault\b|secrets manager|devsecops|\bwaf\b|trivy|snyk|\bopa\b",
    "sre": r"\bslo\b|\bsli\b|incident|on-?call|disaster recovery",
    "linux": r"\blinux\b|rhel",
    "ai": r"\bllm\b|\bmcp\b|ai agents?|agentic|vllm|machine learning|genai|generative ai",
    "cost": r"finops|cost optimi[sz]ation|cloud cost",
    "autoscaling": r"karpenter|autoscal|\bhpa\b",
    "deploys": r"blue[- ]green|canary|release automation",
}
# Titles above your current level rank lower; you can still apply.
TOO_SENIOR_TITLE = re.compile(r"\b(principal|head of|director|vp|chief|staff)\b", re.I)

# --- Scoring ----------------------------------------------------------------

TIER_A = 60  # "Apply now"
TIER_B = 35

# --- The visa itself --------------------------------------------------------

VISA_PAGE = "https://www.immigration.govt.nz/visas/india-skilled-work-visa/"
INZ_EMPLOYER_API = "https://www.immigration.govt.nz/list-api/getAPIResults/"
INZ_EMPLOYER_COLLECTION = "2"

# Jobs posted longer ago than this are dropped from the dashboard.
DROP_AFTER_DAYS = 45
# Full descriptions fetched per run; the rest are fetched on the next run.
MAX_DETAILS_PER_RUN = 150
