from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ====================================== Base Schema ===============================================

class AcademicSessionBase(BaseModel):
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Name of the academic session (e.g., '2024/2025 Session')",
        examples=["2024/2025 Session"]
    )
    start_date: datetime = Field(
        ...,
        description="Start date and time of the academic session"
    )
    end_date: datetime = Field(
        ...,
        description="End date and time of the academic session"
    )

    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start_date(cls, end_date: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and end_date <= start_date:
            raise ValueError("end_date must be strictly after start_date")
        return end_date


# ====================================== Request Schemas ===============================================

class AcademicSessionCreateRequest(AcademicSessionBase):
    """Schema for creating a new academic session."""
    pass


class AcademicSessionUpdateRequest(BaseModel):
    """Schema for partial or full updates of an academic session."""
    name: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Updated name of the academic session"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Updated start date"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Updated end date"
    )

    @field_validator("end_date")
    @classmethod
    def validate_end_date_after_start_date(cls, end_date: Optional[datetime], info) -> Optional[datetime]:
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date <= start_date:
            raise ValueError("end_date must be strictly after start_date")
        return end_date


# ====================================== Response Schema ===============================================

class AcademicSessionResponse(AcademicSessionBase):
    """Schema for serializing academic session database models into API responses."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )