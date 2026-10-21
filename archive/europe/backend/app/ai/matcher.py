from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.gemini_client import generate_json
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class JobMatcher:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def match(
        self,
        resume_text: str,
        skills: list[str],
        job_title: str,
        job_description: str,
        location: str | None = None,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            logger.warning("gemini_api_key missing, returning fallback match")
            return self._fallback()

        prompt = f"""You are an expert engineering recruiter and career coach for Indian DevOps/Platform engineers seeking visa-sponsored jobs in Europe. Evaluate the fit between the candidate profile and a job posting using semantic understanding, not keyword counting. Return valid JSON only with no markdown.

Candidate Profile:
- Resume:
{resume_text[:4000]}

- Skills: {', '.join(skills)}

Job Posting:
- Company: {company_name or 'Unknown'}
- Title: {job_title}
- Location: {location or 'Not specified'}
- Description:
{job_description[:6000]}

Return JSON exactly like this:
{{
  "score": <int 0-100>,
  "reason": "<one paragraph explanation>",
  "strengths": ["<skill/quality 1>", "<skill/quality 2>"],
  "missing_skills": ["<skill 1>", "<skill 2>"],
  "salary_estimate": "<estimated annual range in EUR or GBP, e.g. €80k–€110k>",
  "visa_probability": "<Likely / Possible / Unknown / Not sponsored>",
  "should_apply": <true or false>,
  "confidence": <float 0.0-1.0>,
  "interview_difficulty": "<Easy / Medium / Hard>",
  "predicted_questions": ["<question 1>", "<question 2>", "<question 3>"]
}}

Rules:
- score >= 85 means strong match, recommend applying.
- score 70-84 means good match if missing skills can be learned quickly.
- score < 70 means weak match; should_apply should usually be false unless visa/relocation is explicit.
- Be honest. Do not inflate the score.
- salary_estimate is a rough market range based on role, seniority, and location.
- visa_probability should be "Likely" only if the JD mentions sponsorship, relocation, or international applicants.
""".strip()

        parsed = await generate_json(prompt, model=self.model)
        if not parsed:
            return self._rule_based_fallback(resume_text, skills, job_title, job_description)
        return self._normalize(parsed)

    def _normalize(self, parsed: dict[str, Any]) -> dict[str, Any]:
        return {
            "score": max(0, min(100, int(parsed.get("score", 0)))),
            "reason": str(parsed.get("reason", "")),
            "strengths": parsed.get("strengths") or [],
            "missing_skills": parsed.get("missing_skills") or [],
            "salary_estimate": str(parsed.get("salary_estimate", "")),
            "visa_probability": str(parsed.get("visa_probability", "Unknown")),
            "should_apply": bool(parsed.get("should_apply", False)),
            "confidence": float(parsed.get("confidence", 0.5)),
            "interview_difficulty": str(parsed.get("interview_difficulty", "Medium")),
            "predicted_questions": parsed.get("predicted_questions") or [],
        }

    def _rule_based_fallback(
        self,
        resume_text: str,
        skills: list[str],
        job_title: str,
        job_description: str,
    ) -> dict[str, Any]:
        """Deterministic scoring used when the Gemini API is unavailable or rate-limited."""
        text = f"{job_title} {job_description or ''}".lower()
        resume = resume_text.lower()

        known_skills = [
            "kubernetes", "terraform", "aws", "azure", "gcp", "docker", "python",
            "ci/cd", "github actions", "gitlab ci", "jenkins", "ansible", "prometheus",
            "grafana", "linux", "bash", "go", "rust", "java", "sql", "nosql",
            "postgresql", "mysql", "redis", "kafka", "elasticsearch", "nginx",
            "helm", "argo cd", "flux", "pulumi", "cloudformation", "sre",
        ]
        skill_pool = {s.lower() for s in skills}
        if not skill_pool:
            skill_pool = {s for s in known_skills if s in resume}

        matched_skills = [s for s in skill_pool if s in text]
        resume_tokens = set(resume.split())
        overlap = [token for token in text.split() if token in resume_tokens]
        overlap_score = min(100, len(overlap) * 2) if text else 0

        title_score = 0
        target_keywords = ["devops", "platform", "sre", "site reliability", "infrastructure", "cloud", "reliability"]
        for kw in target_keywords:
            if kw in f"{job_title}".lower():
                title_score += 15

        visa_score = 0
        visa_keywords = ["visa", "sponsorship", "relocation", "international", "global talent", "blue card"]
        for kw in visa_keywords:
            if kw in text:
                visa_score += 10

        score = min(100, overlap_score + title_score + min(visa_score, 20) + (len(matched_skills) * 8))
        should_apply = score >= 65

        return {
            "score": score,
            "reason": "Rule-based fallback: Gemini API unavailable or rate-limited. Score is based on keyword/skill overlap.",
            "strengths": matched_skills[:5],
            "missing_skills": [],
            "salary_estimate": "",
            "visa_probability": "Likely sponsorship" if visa_score >= 10 else "Possible sponsorship",
            "should_apply": should_apply,
            "confidence": 0.5,
            "interview_difficulty": "Medium",
            "predicted_questions": [],
        }

    def _fallback(self) -> dict[str, Any]:
        return {
            "score": 0,
            "reason": "AI matching unavailable. Manual review required.",
            "strengths": [],
            "missing_skills": [],
            "salary_estimate": "",
            "visa_probability": "Unknown",
            "should_apply": False,
            "confidence": 0.0,
            "interview_difficulty": "Medium",
            "predicted_questions": [],
        }
