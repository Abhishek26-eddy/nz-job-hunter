from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResumeBase(BaseModel):
    name: str
    is_master: bool = False
    content_text: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    tailored_for_job_id: Optional[int] = None


class ResumeCreate(ResumeBase):
    user_id: int


class ResumeRead(ResumeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    profile: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
