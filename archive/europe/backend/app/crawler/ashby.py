from datetime import datetime
from typing import Any

import httpx
import structlog

from app.crawler.base import BaseJobCrawler, RawJobPosting

logger = structlog.get_logger()


class AshbyCrawler(BaseJobCrawler):
    platform = "ashby"

    async def fetch_jobs(
        self, company_identifier: str, company_id: int
    ) -> list[RawJobPosting]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company_identifier}"
        jobs: list[RawJobPosting] = []

        async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": self.user_agent}) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                logger.warning(
                    "ashby_fetch_failed",
                    company=company_identifier,
                    error=str(exc),
                )
                return jobs

        postings = data.get("jobs", [])
        for item in postings:
            title = item.get("title", "")
            if not self.is_target_role(title):
                continue

            location_parts = []
            if item.get("location"):
                loc = item["location"]
                if isinstance(loc, dict):
                    city = loc.get("city")
                    country = loc.get("country")
                    if city:
                        location_parts.append(city)
                    if country:
                        location_parts.append(country)
                else:
                    location_parts.append(str(loc))

            jobs.append(
                RawJobPosting(
                    external_id=str(item.get("id", "")),
                    platform=self.platform,
                    title=title,
                    description=item.get("description", ""),
                    location=", ".join(location_parts) if location_parts else None,
                    workplace_type=item.get("employmentType"),
                    employment_type=None,
                    salary_min=None,
                    salary_max=None,
                    salary_currency=None,
                    salary_period=None,
                    application_url=item.get("jobUrl", ""),
                    posted_at=None,
                    url=item.get("jobUrl", ""),
                    raw_data=item,
                )
            )

        logger.info(
            "ashby_jobs_fetched",
            company=company_identifier,
            matched=len(jobs),
            total=len(postings),
        )
        return jobs
