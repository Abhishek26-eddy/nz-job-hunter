from typing import Any

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.gemini_client import generate_json
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class CoverLetterGenerator:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def generate(
        self,
        resume_text: str,
        job_title: str,
        job_description: str,
        company_name: str | None = None,
        max_words: int = 250,
    ) -> dict[str, Any]:
        if not self.api_key:
            return {"content": "", "word_count": 0}

        prompt = f"""Write a concise, professional cover letter for the role below. Use the candidate's resume as source material. Do not invent experience or skills. Maximum {max_words} words.

Company: {company_name or 'Unknown'}
Role: {job_title}
Job Description:
{job_description[:4000]}

Candidate Resume:
{resume_text[:3000]}

Return JSON:
{{
  "content": "<cover letter text with paragraphs separated by double newlines>",
  "word_count": <int>
}}
""".strip()

        parsed = await generate_json(prompt, model=self.model)
        if not parsed:
            return {"content": "", "word_count": 0}
        return {
            "content": str(parsed.get("content", "")),
            "word_count": int(parsed.get("word_count", 0)),
        }
