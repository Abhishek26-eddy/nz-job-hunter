import asyncio
from typing import Any

import google.generativeai as genai
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


def configure_gemini(api_key: str | None = None) -> None:
    key = api_key or get_settings().gemini_api_key
    if key:
        genai.configure(api_key=key)


def _get_model(model: str | None = None) -> genai.GenerativeModel:
    configure_gemini()
    name = model or get_settings().gemini_model
    return genai.GenerativeModel(model_name=name)


async def generate_json(prompt: str, model: str | None = None) -> dict[str, Any]:
    """Ask Gemini for JSON and return the parsed object. Falls back to an empty dict."""
    settings = get_settings()
    if not settings.gemini_api_key:
        logger.warning("gemini_api_key missing, returning empty AI result")
        return {}

    loop = asyncio.get_event_loop()
    m = _get_model(model)
    try:
        response = await loop.run_in_executor(
            None,
            lambda: m.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 2000},
                safety_settings={
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                },
            ),
        )
        text = response.text
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        import json

        return json.loads(cleaned)
    except Exception as exc:
        logger.error("gemini_generate_failed", error=str(exc))
        return {}
