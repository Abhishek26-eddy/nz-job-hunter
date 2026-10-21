from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.gemini_client import generate_json
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class ResumeTailor:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def tailor(
        self,
        master_resume_text: str,
        job_title: str,
        job_description: str,
        company_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.api_key:
            return {"tailored_text": master_resume_text, "highlighted_skills": [], "summary": ""}

        prompt = f"""You are a resume optimizer. Tailor the resume below for this job without lying or inventing experience. Only reorder, rephrase, and emphasize relevant bullets. Do not add skills or roles the candidate does not have.

Job:
- Company: {company_name or 'Unknown'}
- Title: {job_title}
- Description:
{job_description[:5000]}

Master Resume:
{master_resume_text[:5000]}

Return JSON:
{{
  "tailored_text": "<full tailored resume text>",
  "highlighted_skills": ["<skill 1>", "<skill 2>"],
  "summary": "<2-3 sentence profile summary tailored to the role>"
}}
""".strip()

        parsed = await generate_json(prompt, model=self.model)
        if not parsed:
            return {"tailored_text": master_resume_text, "highlighted_skills": [], "summary": ""}
        return {
            "tailored_text": str(parsed.get("tailored_text", master_resume_text)),
            "highlighted_skills": parsed.get("highlighted_skills") or [],
            "summary": str(parsed.get("summary", "")),
        }
