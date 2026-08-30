from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


# Base schema containing shared term fields
class TermBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_current: Optional[bool] = False
    academic_session_id: int

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v


# Schema used for creating a term
class TermCreateRequest(TermBase):
    pass


# Schema used for updating term metadata (all fields optional)
class TermUpdateRequest(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("name cannot be blank")
        return v


# Schema used for reassigning a term to a different academic session
class TermReassignSessionRequest(BaseModel):
    academic_session_id: int


# Schema used for serializing term data in API responses
class TermResponse(TermBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)