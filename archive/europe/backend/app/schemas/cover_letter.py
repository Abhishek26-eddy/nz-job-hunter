from typing import Optional

from pydantic import BaseModel, ConfigDict


class CoverLetterBase(BaseModel):
    user_id: int
    job_id: int
    title: str
    content: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    word_count: int = 0


class CoverLetterCreate(CoverLetterBase):
    pass


class CoverLetterRead(CoverLetterBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
