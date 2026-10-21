from typing import Optional

from pydantic import BaseModel, ConfigDict


class CountryBase(BaseModel):
    name: str
    code: str
    region: Optional[str] = None
    is_eu: bool = False
    visa_notes: Optional[str] = None


class CountryCreate(CountryBase):
    pass


class CountryRead(CountryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
