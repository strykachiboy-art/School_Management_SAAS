from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ====================================== Base Schema ===============================================

class SectionBase(BaseModel):
    level_id: int = Field(..., description="ID of the parent AcademicLevel")
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the section (e.g., 'A', 'Blue', 'Science')",
        examples=["A"],
    )
    display_order: int = Field(0, description="Sort order relative to other sections in the same level")


# ====================================== Request Schemas ===============================================

class SectionCreateRequest(SectionBase):
    """Schema for creating a new section under a level."""
    pass


class SectionUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


# ====================================== Response Schema ===============================================

class SectionResponse(SectionBase):
    """Schema for serializing section database models into API responses."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)