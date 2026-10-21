"""Company discovery from ATS URLs/career pages.

The discovery engine:
- Accepts a list of candidate companies (name + career_page_url, optionally country/city).
- Detects the ATS provider from the URL.
- Extracts the ATS-specific board identifier.
- Creates or updates the company record.
- Never invents synthetic company names.
"""

import re
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.country import Country

logger = structlog.get_logger()


# Map URL patterns to ATS providers. Order matters: more specific patterns first.
ATS_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("greenhouse", re.compile(r"boards\.greenhouse\.io/(?P<identifier>[^/\s]+)", re.I)),
    ("greenhouse", re.compile(r"boards-api\.greenhouse\.io/v1/boards/(?P<identifier>[^/\s]+)", re.I)),
    ("greenhouse", re.compile(r"greenhouse\.io/(?P<identifier>[^/\s]+)", re.I)),
    ("lever", re.compile(r"jobs\.lever\.co/(?P<identifier>[^/\s]+)", re.I)),
    ("lever", re.compile(r"api\.lever\.co/v0/postings/(?P<identifier>[^/\s]+)", re.I)),
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/(?P<identifier>[^/\s]+)", re.I)),
    ("ashby", re.compile(r"api\.ashbyhq\.com/posting-api/job-board/(?P<identifier>[^/\s]+)", re.I)),
    ("teamtailor", re.compile(r"(?P<identifier>[a-z0-9-]+)\.teamtailor\.com", re.I)),
    ("smartrecruiters", re.compile(r"jobs\.smartrecruiters\.com/(?P<identifier>[^/\s]+)", re.I)),
    ("personio", re.compile(r"(?P<identifier>[a-z0-9-]+)\.jobs\.personio\.de", re.I)),
    ("workday", re.compile(r"(?P<identifier>[a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com", re.I)),
    ("workday", re.compile(r"myworkdayjobs\.com/(?P<identifier>[^/\s]+)", re.I)),
    ("workable", re.compile(r"apply\.workable\.com/(?P<identifier>[^/\s]+)", re.I)),
]


class CompanyDiscoveryError(Exception):
    pass


class CompanyDiscoveryService:
    """Detect ATS providers from career-page URLs and upsert real companies."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._country_cache: dict[str, int | None] | None = None

    async def _load_country_cache(self) -> dict[str, int | None]:
        if self._country_cache is None:
            rows = (await self.db.execute(select(Country))).scalars().all()
            self._country_cache = {c.code.upper(): c.id for c in rows}
        return self._country_cache

    @staticmethod
    def detect_ats(url: str | None) -> tuple[str | None, str | None]:
        """Return (ats_provider, board_identifier) for a career-page URL."""
        if not url:
            return None, None
        for provider, pattern in ATS_PATTERNS:
            match = pattern.search(url)
            if match:
                identifier = match.group("identifier")
                return provider, identifier
        return None, None

    async def upsert(
        self,
        name: str,
        career_page_url: str | None = None,
        website: str | None = None,
        country_code: str | None = None,
        city: str | None = None,
        industry: str | None = None,
        size: str | None = None,
        visa_sponsorship: str | None = None,
        remote_policy: str | None = None,
        engineering_blog_url: str | None = None,
        known_tech_stack: list[str] | None = None,
        source: str = "discovery",
    ) -> tuple[Company, bool]:
        """Create or update a company discovered through an ATS URL.

        Returns the company and a boolean indicating whether it was newly created.
        """
        name = (name or "").strip()
        if not name:
            raise CompanyDiscoveryError("Company name is required")

        slug = _slugify(name)
        ats_provider, ats_identifier = self.detect_ats(career_page_url)
        ats_config: dict[str, Any] = {}
        if ats_provider and ats_identifier:
            ats_config["board_name"] = ats_identifier

        country_cache = await self._load_country_cache()
        country_id = country_cache.get((country_code or "").upper()) if country_code else None

        existing = (
            await self.db.execute(select(Company).where(Company.slug == slug))
        ).scalar_one_or_none()

        now = datetime.utcnow()
        if existing:
            updated = False
            if career_page_url and not existing.career_page_url:
                existing.career_page_url = career_page_url
                updated = True
            if website and not existing.website:
                existing.website = website
                updated = True
            if ats_provider and (not existing.ats_provider or existing.ats_provider == "Unknown"):
                existing.ats_provider = ats_provider
                existing.ats_config = {**existing.ats_config, **ats_config}
                existing.ats_changes = (existing.ats_changes or 0) + 1
                updated = True
            if ats_config and "board_name" in ats_config:
                existing.ats_config = {**existing.ats_config, **ats_config}
                updated = True
            if country_id and not existing.country_id:
                existing.country_id = country_id
                updated = True
            if city and not existing.city:
                existing.city = city
                updated = True
            if industry and not existing.industry:
                existing.industry = industry
                updated = True
            if size and not existing.size:
                existing.size = size
                updated = True
            if visa_sponsorship:
                existing.visa_sponsorship = visa_sponsorship
                updated = True
            if remote_policy and not existing.remote_policy:
                existing.remote_policy = remote_policy
                updated = True
            if engineering_blog_url and not existing.engineering_blog_url:
                existing.engineering_blog_url = engineering_blog_url
                updated = True
            if known_tech_stack:
                existing.public_tech_stack = list(set((existing.public_tech_stack or []) + known_tech_stack))
                updated = True

            existing.last_seen = now
            if updated:
                existing.updated_at = now
                logger.info("company_updated_via_discovery", slug=slug, source=source)
            return existing, False

        company = Company(
            name=name,
            slug=slug,
            website=website or career_page_url,
            career_page_url=career_page_url,
            engineering_blog_url=engineering_blog_url,
            ats_provider=ats_provider or "Unknown",
            ats_config=ats_config,
            ats_changes=1 if ats_provider else 0,
            industry=industry,
            size=size,
            country_id=country_id,
            city=city,
            visa_sponsorship=visa_sponsorship or "Unknown",
            remote_policy=remote_policy,
            remote_friendly=remote_policy in ("remote-first", "fully remote"),
            hiring_status="active",
            is_active=True,
            known_tech_stack=known_tech_stack or [],
            public_tech_stack=known_tech_stack or [],
            first_seen=now,
            last_seen=now,
            last_crawled=None,
            jobs_found=0,
        )
        self.db.add(company)
        logger.info("company_created_via_discovery", name=name, slug=slug, ats=ats_provider, source=source)
        return company, True

    async def ingest(
        self,
        candidates: list[dict[str, Any]],
        source: str = "discovery",
    ) -> dict[str, Any]:
        """Ingest a batch of discovered companies.

        Returns summary counts.
        """
        created = 0
        updated = 0
        skipped = 0
        for candidate in candidates:
            candidate = dict(candidate)
            name = candidate.pop("name", "").strip()
            if not name:
                skipped += 1
                continue
            try:
                _, was_created = await self.upsert(name=name, source=source, **candidate)
                if was_created:
                    created += 1
                else:
                    updated += 1
            except CompanyDiscoveryError:
                skipped += 1
                logger.warning("discovery_candidate_skipped", candidate=candidate)

        await self.db.commit()
        return {"created": created, "updated": updated, "skipped": skipped, "total": len(candidates)}


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace(",", "")
        .replace("/", "-")
        .replace("&", "and")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("--", "-")
        [:64]
    )
