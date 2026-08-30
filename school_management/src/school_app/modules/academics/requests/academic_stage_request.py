from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ====================================== Base Schema ===============================================

class AcademicStageBase(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Name of the academic stage (e.g., 'Junior Secondary', 'Middle School')",
        examples=["Junior Secondary"],
    )
    display_order: int = Field(
        0,
        description="Sort order relative to other stages",
    )


# ====================================== Request Schemas ===============================================

class AcademicStageCreateRequest(AcademicStageBase):
    """Schema for creating a new academic stage."""
    pass


class AcademicStageUpdateRequest(BaseModel):
    """Schema for partial updates of an academic stage."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ====================================== Response Schema ===============================================

class AcademicStageResponse(AcademicStageBase):
    """Schema for serializing academic stage database models into API responses."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)