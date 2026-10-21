from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class RawJobPosting:
    external_id: str
    platform: str
    title: str
    description: str
    location: str | None
    workplace_type: str | None
    employment_type: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_period: str | None
    application_url: str | None
    posted_at: datetime | None
    url: str
    raw_data: dict[str, Any]


class BaseJobCrawler(ABC):
    platform: str = "unknown"

    def __init__(self, user_agent: str | None = None):
        self.user_agent = user_agent or "EuropeJobAgent/1.0"

    @abstractmethod
    async def fetch_jobs(
        self, company_identifier: str, company_id: int
    ) -> list[RawJobPosting]:
        raise NotImplementedError

    def is_target_role(self, title: str) -> bool:
        title_lower = title.lower()
        keywords = [
            # Core platform / infra / SRE / DevOps
            "devops", "platform engineer", "cloud engineer", "infrastructure engineer",
            "site reliability engineer", "sre", "aws engineer", "cloud platform",
            "platform reliability", "kubernetes", "terraform", "infrastructure",
            "cloud operations", "platform operations", "site operations",
            "production engineer", "production services", "production orchestration",
            "reliability engineer", "systems engineer", "distributed systems engineer",
            "observability engineer", "monitoring engineer", "performance engineer",
            # Security
            "cloud security", "security engineer", "cyber security", "information security",
            "network security", "application security", "secops", "infosec",
            "devsecops",
            # Senior IC titles that often host relevant sub-teams
            "member of technical staff",
            "software engineer - platform", "software engineer - infrastructure",
            "software engineer - cloud", "software engineer - devops",
            "software engineer - site reliability", "software engineer - sre",
            "software engineer - security", "software engineer - production",
            "software engineer - vitess", "software engineer - neki",
        ]
        exclude = [
            "frontend", "backend engineer", "data scientist", "qa engineer", "support engineer",
            "product manager", "program manager", "project manager", "account executive",
            "sales", "marketing", "recruiter", "talent", "customer support", "customer success",
            "business analyst", "finance", "legal", "hr ", "people ", "operations manager",
        ]
        if any(ex in title_lower for ex in exclude):
            return False
        return any(kw in title_lower for kw in keywords)
