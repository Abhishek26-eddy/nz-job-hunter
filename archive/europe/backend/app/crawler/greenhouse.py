from datetime import datetime
from typing import Any

import httpx
import structlog

from app.crawler.base import BaseJobCrawler, RawJobPosting

logger = structlog.get_logger()


class GreenhouseCrawler(BaseJobCrawler):
    platform = "greenhouse"

    async def fetch_jobs(
        self, company_identifier: str, company_id: int
    ) -> list[RawJobPosting]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company_identifier}/jobs"
        jobs: list[RawJobPosting] = []

        async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": self.user_agent}) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.warning(
                    "greenhouse_fetch_failed",
                    company=company_identifier,
                    error=str(exc),
                )
                return jobs

        for item in data.get("jobs", []):
            title = item.get("title", "")
            if not self.is_target_role(title):
                continue

            location = item.get("location", {})
            location_name = location.get("name") if isinstance(location, dict) else str(location)
            meta = item.get("metadata", []) or []
            workplace_type = self._extract_meta(meta, ["workplace", "remote"])
            employment_type = self._extract_meta(meta, ["employment", "job type"])

            absolute_url = item.get("absolute_url", "")
            jobs.append(
                RawJobPosting(
                    external_id=str(item.get("id", "")),
                    platform=self.platform,
                    title=title,
                    description=item.get("content", "") or item.get("description", ""),
                    location=location_name,
                    workplace_type=workplace_type,
                    employment_type=employment_type,
                    salary_min=None,
                    salary_max=None,
                    salary_currency=None,
                    salary_period=None,
                    application_url=absolute_url,
                    posted_at=None,
                    url=absolute_url,
                    raw_data=item,
                )
            )

        logger.info(
            "greenhouse_jobs_fetched",
            company=company_identifier,
            matched=len(jobs),
            total=len(data.get("jobs", [])),
        )
        return jobs

    def _extract_meta(self, meta: list[dict[str, Any]], keys: list[str]) -> str | None:
        for entry in meta:
            name = str(entry.get("name", "")).lower()
            if any(k in name for k in keys):
                value = entry.get("value")
                if isinstance(value, str):
                    return value
                if isinstance(value, dict):
                    return value.get("name") or value.get("value")
        return None
