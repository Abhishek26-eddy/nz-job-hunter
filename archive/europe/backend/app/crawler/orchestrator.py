import asyncio
import hashlib
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.crawler.ashby import AshbyCrawler
from app.crawler.base import BaseJobCrawler, RawJobPosting
from app.crawler.greenhouse import GreenhouseCrawler
from app.crawler.lever import LeverCrawler
from app.db.session import AsyncSessionLocal
from app.models.company import Company
from app.models.job import Job
from app.services.company_discovery import CompanyDiscoveryService

logger = structlog.get_logger()
settings = get_settings()


CRAWLERS: dict[str, type[BaseJobCrawler]] = {
    "greenhouse": GreenhouseCrawler,
    "lever": LeverCrawler,
    "ashby": AshbyCrawler,
}


class CrawlerOrchestrator:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.user_agent = settings.user_agent
        self._session_owned = db is None
        # AsyncSession is not safe for concurrent use across asyncio tasks;
        # serialize all DB reads/writes while still fetching jobs over HTTP
        # concurrently.
        self._db_lock = asyncio.Lock()

    async def __aenter__(self):
        if self._session_owned:
            self.db = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session_owned and self.db:
            await self.db.close()

    async def discover_for_company(
        self, company: Company, identifier: str | None = None
    ) -> list[Job]:
        # Auto-detect ATS from the career page URL if it is missing or unknown.
        # Mutates the (shared) Company ORM object, so serialize with the lock.
        async with self._db_lock:
            if not company.ats_provider or company.ats_provider.lower() in ("unknown", "internal", ""):
                detected_ats, detected_identifier = CompanyDiscoveryService.detect_ats(
                    company.career_page_url
                )
                if detected_ats:
                    company.ats_provider = detected_ats
                    company.ats_config = {**company.ats_config, "board_name": detected_identifier}
                    company.ats_changes = (company.ats_changes or 0) + 1
                    logger.info(
                        "ats_auto_detected",
                        company=company.name,
                        ats=detected_ats,
                        identifier=detected_identifier,
                    )

            if (company.ats_provider or "").lower() not in CRAWLERS:
                return []
            ats_provider = (company.ats_provider or "").lower()
            ats_identifier = identifier or company.ats_config.get("board_name") or company.slug

        crawler_cls = CRAWLERS[ats_provider]
        crawler = crawler_cls(user_agent=self.user_agent)

        try:
            # Network I/O only; safe to run concurrently across companies.
            raw_jobs = await crawler.fetch_jobs(ats_identifier, company.id)
        except Exception as exc:
            logger.error(
                "crawl_company_failed",
                company=company.name,
                ats=company.ats_provider,
                error=str(exc),
            )
            return []

        # All AsyncSession access (queries, inserts, flush) must be serialized.
        async with self._db_lock:
            created: list[Job] = []
            for raw in raw_jobs:
                job = await self._upsert_job(company, raw)
                if job:
                    created.append(job)

            # Track per-company quality stats.
            now = datetime.utcnow()
            company.last_crawled = now
            company.last_seen = now
            company.jobs_found = (company.jobs_found or 0) + len(created)

            await self.db.flush()
        return created

    async def run_batch(self, limit: int = 50) -> dict[str, Any]:
        result: dict[str, Any] = {"companies": 0, "jobs": 0, "new_job_ids": []}
        query = (
            select(Company)
            .where(Company.is_active == True)
            .where(func.lower(Company.ats_provider).in_(list(CRAWLERS.keys())))
            .order_by(Company.updated_at.asc())
            .limit(limit)
        )
        companies = (await self.db.execute(query)).scalars().all()

        semaphore = asyncio.Semaphore(settings.max_concurrent_crawls)

        async def crawl_one(company: Company):
            async with semaphore:
                return await self.discover_for_company(company)

        tasks = [crawl_one(c) for c in companies]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for company, res in zip(companies, batch_results):
            result["companies"] += 1
            if isinstance(res, list):
                result["jobs"] += len(res)
                for job in res:
                    result["new_job_ids"].append(job.id)
            else:
                logger.error("batch_crawl_exception", company=company.name, error=str(res))

        await self.db.commit()
        return result

    async def _upsert_job(self, company: Company, raw: RawJobPosting) -> Job | None:
        description_hash = hashlib.sha256(raw.description.encode("utf-8")).hexdigest()

        existing = (
            await self.db.execute(
                select(Job).where(
                    Job.external_id == raw.external_id,
                    Job.platform == raw.platform,
                    Job.company_id == company.id,
                )
            )
        ).scalar_one_or_none()

        if existing:
            await self._update_existing(existing, raw, description_hash)
            return None

        def trunc(value: str | None, length: int) -> str | None:
            if value and isinstance(value, str) and len(value) > length:
                return value[:length]
            return value

        job = Job(
            external_id=trunc(raw.external_id, 255),
            platform=trunc(raw.platform, 64),
            platform_url=trunc(raw.url, 1024),
            title=trunc(raw.title, 512),
            description=raw.description,
            description_hash=description_hash,
            location=trunc(raw.location, 255),
            workplace_type=trunc(raw.workplace_type, 32),
            employment_type=trunc(raw.employment_type, 32),
            salary_min=raw.salary_min,
            salary_max=raw.salary_max,
            salary_currency=trunc(raw.salary_currency, 8),
            salary_period=trunc(raw.salary_period, 16),
            application_url=trunc(raw.application_url, 1024),
            posted_at=raw.posted_at or datetime.utcnow(),
            company_id=company.id,
            country_id=company.country_id,
            raw_data=raw.raw_data,
        )
        self.db.add(job)
        return job

    async def _update_existing(
        self, existing: Job, raw: RawJobPosting, description_hash: str
    ) -> None:
        changed: list[str] = []
        if existing.description_hash != description_hash:
            changed.append("description")
            existing.description = raw.description
            existing.description_hash = description_hash
        if existing.title != raw.title:
            changed.append("title")
            existing.title = raw.title[:512] if raw.title else raw.title
        if existing.location != raw.location:
            changed.append("location")
            existing.location = raw.location[:255] if raw.location else raw.location

        if changed:
            existing.updated_at = datetime.utcnow()
            # Snapshot logic could be added here
            logger.info("job_updated", job_id=existing.id, changes=changed)
