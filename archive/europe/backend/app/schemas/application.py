from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.job import JobRead


class ApplicationBase(BaseModel):
    job_id: int
    resume_id: Optional[int] = None
    cover_letter_id: Optional[int] = None
    status: str = "saved"
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    applied_at: Optional[datetime] = None
    response_at: Optional[datetime] = None
    response_time_days: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    job: Optional[JobRead] = None
