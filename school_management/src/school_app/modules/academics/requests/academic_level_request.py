from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ====================================== Base Schema ===============================================

class AcademicLevelBase(BaseModel):
    stage_id: int = Field(..., description="ID of the parent AcademicStage")
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the level (e.g., 'JSS 1', 'Grade 7', 'Year 8')",
        examples=["JSS 1"],
    )
    display_order: int = Field(0, description="Sort order relative to other levels in the same stage")


# ====================================== Request Schemas ===============================================

class AcademicLevelCreateRequest(AcademicLevelBase):
    """Schema for creating a new academic level under a stage."""
    pass


class AcademicLevelUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ====================================== Response Schema ===============================================

class AcademicLevelResponse(AcademicLevelBase):
    """Schema for serializing academic level database models into API responses."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)