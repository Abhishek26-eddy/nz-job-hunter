from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.country import CountryRead


class CompanyBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    website: Optional[str] = None
    career_page_url: Optional[str] = None
    engineering_blog_url: Optional[str] = None
    ats_provider: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    city: Optional[str] = None
    country_id: Optional[int] = None
    employee_count: Optional[int] = None
    visa_sponsorship: str = "Unknown"
    relocation_assistance: bool = False
    remote_policy: Optional[str] = None
    remote_friendly: bool = False
    hiring_status: str = "active"
    glassdoor_rating: Optional[float] = None
    known_tech_stack: Optional[List[str]] = Field(default_factory=list)
    public_tech_stack: Optional[List[str]] = Field(default_factory=list)


class CompanyCreate(CompanyBase):
    ats_config: dict = Field(default_factory=dict)
    ats_changes: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_crawled: Optional[datetime] = None
    jobs_found: int = 0


class CompanyUpdate(BaseModel):
    description: Optional[str] = None
    website: Optional[str] = None
    career_page_url: Optional[str] = None
    engineering_blog_url: Optional[str] = None
    ats_provider: Optional[str] = None
    ats_config: Optional[dict] = None
    ats_changes: Optional[int] = None
    visa_sponsorship: Optional[str] = None
    relocation_assistance: Optional[bool] = None
    remote_policy: Optional[str] = None
    remote_friendly: Optional[bool] = None
    hiring_status: Optional[str] = None
    glassdoor_rating: Optional[float] = None
    known_tech_stack: Optional[List[str]] = None
    public_tech_stack: Optional[List[str]] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_crawled: Optional[datetime] = None
    jobs_found: Optional[int] = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ats_config: dict
    ats_changes: int
    is_active: bool
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    last_crawled: Optional[datetime] = None
    jobs_found: int
    country: Optional[CountryRead] = None
