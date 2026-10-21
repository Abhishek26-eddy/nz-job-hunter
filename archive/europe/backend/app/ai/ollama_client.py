"""Lightweight async client for a local Ollama instance."""

import json
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()
_settings = get_settings()


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        fallback_model: str | None = None,
    ):
        self.base_url = (base_url or _settings.ollama_url).rstrip("/")
        self.model = model or _settings.ollama_model
        self.fallback_model = fallback_model or _settings.ollama_fallback_model

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                data = resp.json()
                names = {m.get("name", "") for m in data.get("models", [])}
                return self.model in names or self.fallback_model in names
        except Exception as exc:
            logger.debug("ollama_unavailable", error=str(exc))
            return False

    def _effective_model(self, available_models: set[str]) -> str:
        if self.model in available_models:
            return self.model
        if self.fallback_model in available_models:
            logger.warning("ollama_fallback_model_used", fallback=self.fallback_model)
            return self.fallback_model
        raise OllamaError(f"Neither {self.model} nor {self.fallback_model} is installed locally")

    async def generate_json(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.3,
        timeout: float = 120,
    ) -> dict[str, Any]:
        """Ask Ollama for a JSON object. Returns {} if Ollama is unreachable."""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                tags_resp = await client.get(f"{self.base_url}/api/tags")
                if tags_resp.status_code != 200:
                    return {}
                available = {m.get("name", "") for m in tags_resp.json().get("models", [])}
                effective_model = model or self._effective_model(available)

                payload = {
                    "model": effective_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"temperature": temperature},
                }
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                text = resp.json().get("response", "")
                return json.loads(text.strip())
        except Exception as exc:
            logger.error("ollama_generate_failed", error=str(exc))
            return {}
