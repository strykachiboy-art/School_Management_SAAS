# src/school_app/modules/academics/requests/academic_session_request.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class AcademicSessionBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, examples=["2024/2025 Session"])
    start_date: datetime = Field(..., description="ISO 8601 start date/time")
    end_date: datetime = Field(..., description="ISO 8601 end date/time")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start_date(cls, end_date: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and end_date <= start_date:
            raise ValueError("end_date must be strictly after start_date")
        return end_date


class AcademicSessionCreateRequest(AcademicSessionBase):
    school_id: Optional[int] = Field(None, description="School id for the session; derived from actor if omitted")


class AcademicSessionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def strip_name_optional(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start_date(cls, end_date: Optional[datetime], info) -> Optional[datetime]:
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date <= start_date:
            raise ValueError("end_date must be strictly after start_date")
        return end_date


class AcademicSessionResponse(AcademicSessionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
