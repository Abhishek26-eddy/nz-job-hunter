from datetime import datetime
from typing import Any

import httpx
import structlog

from app.crawler.base import BaseJobCrawler, RawJobPosting

logger = structlog.get_logger()


class LeverCrawler(BaseJobCrawler):
    platform = "lever"

    async def fetch_jobs(
        self, company_identifier: str, company_id: int
    ) -> list[RawJobPosting]:
        url = f"https://api.lever.co/v0/postings/{company_identifier}?mode=json"
        jobs: list[RawJobPosting] = []

        async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": self.user_agent}) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.warning(
                    "lever_fetch_failed",
                    company=company_identifier,
                    error=str(exc),
                )
                return jobs

        postings = data if isinstance(data, list) else data.get("postings", [])
        for item in postings:
            title = item.get("text", "")
            if not self.is_target_role(title):
                continue

            workplace_type = self._extract_workplace_type(item)
            employment_type = None

            jobs.append(
                RawJobPosting(
                    external_id=str(item.get("id", "")),
                    platform=self.platform,
                    title=title,
                    description=item.get("description", ""),
                    location=self._format_location(item.get("categories", {}).get("location")),
                    workplace_type=workplace_type,
                    employment_type=employment_type,
                    salary_min=None,
                    salary_max=None,
                    salary_currency=None,
                    salary_period=None,
                    application_url=item.get("hostedUrl", ""),
                    posted_at=None,
                    url=item.get("hostedUrl", ""),
                    raw_data=item,
                )
            )

        logger.info(
            "lever_jobs_fetched",
            company=company_identifier,
            matched=len(jobs),
            total=len(postings),
        )
        return jobs

    def _format_location(self, location: Any) -> str | None:
        if isinstance(location, str):
            return location
        if isinstance(location, list):
            return ", ".join(str(x) for x in location)
        return None

    def _extract_workplace_type(self, item: dict[str, Any]) -> str | None:
        cats = item.get("categories", {})
        commitment = str(cats.get("commitment", "")).lower()
        if "remote" in commitment:
            return "remote"
        if "hybrid" in commitment:
            return "hybrid"
        if "onsite" in commitment or "on-site" in commitment:
            return "onsite"
        return None
