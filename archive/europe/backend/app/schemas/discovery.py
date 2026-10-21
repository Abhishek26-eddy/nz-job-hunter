from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CompanyDiscoveryCandidate(BaseModel):
    name: str = Field(..., min_length=1, description="Official company name")
    career_page_url: HttpUrl | None = None
    website: HttpUrl | None = None
    country_code: str | None = Field(default=None, max_length=4)
    city: str | None = None
    industry: str | None = None
    size: str | None = None
    visa_sponsorship: str | None = None
    remote_policy: str | None = None
    engineering_blog_url: HttpUrl | None = None
    known_tech_stack: list[str] = Field(default_factory=list)


class CompanyDiscoveryRequest(BaseModel):
    candidates: list[CompanyDiscoveryCandidate] = Field(..., min_length=1)
    source: str = "manual"


class CompanyDiscoverySummary(BaseModel):
    created: int
    updated: int
    skipped: int
    total: int
