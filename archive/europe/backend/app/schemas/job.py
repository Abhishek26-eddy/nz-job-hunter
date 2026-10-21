from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.company import CompanyRead


class JobBase(BaseModel):
    external_id: str
    platform: str
    platform_url: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    workplace_type: Optional[str] = None  # remote / hybrid / onsite
    employment_type: Optional[str] = None  # full-time / contract
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    salary_period: Optional[str] = None
    application_url: Optional[str] = None
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    company_id: int
    country_id: Optional[int] = None


class JobCreate(JobBase):
    description_hash: str
    raw_data: dict = Field(default_factory=dict)


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    is_active: Optional[bool] = None
    match_score: Optional[float] = None
    should_apply: Optional[bool] = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description_hash: str
    is_active: bool
    is_deleted: bool
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    strengths: Optional[List[str]] = Field(default_factory=list)
    missing_skills: Optional[List[str]] = Field(default_factory=list)
    visa_sponsorship_inferred: str
    salary_estimate: Optional[str] = None
    should_apply: Optional[bool] = None
    confidence: Optional[float] = None
    tech_stack: Optional[List[str]] = Field(default_factory=list)
    role_category: Optional[str] = None
    role_priority: Optional[str] = None
    rejected: bool = False
    rejection_reason: Optional[str] = None
    score_breakdown: Optional[dict] = None
    critical_missing_skills: Optional[List[str]] = Field(default_factory=list)
    application_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    company: Optional[CompanyRead] = None


class JobFilter(BaseModel):
    search: Optional[str] = None
    country_id: Optional[int] = None
    country_code: Optional[str] = None
    workplace_type: Optional[str] = None
    min_match_score: Optional[float] = None
    should_apply: Optional[bool] = None
    visa_sponsorship_inferred: Optional[str] = None
    remote: Optional[bool] = None
    skills: Optional[List[str]] = None
    company_size: Optional[str] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    status: Optional[str] = None  # saved, applied, etc.
    role_priority: Optional[str] = None
    include_rejected: bool = False
