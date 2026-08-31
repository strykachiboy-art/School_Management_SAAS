# src/school_app/modules/academics/requests/academic_stage_request.py

from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class AcademicStageCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Stage name")
    code: Optional[str] = Field(None, description="Short string code, e.g. 'SS'")
    num_code: Optional[int] = Field(None, description="Numeric code, e.g. 0")
    display_order: Optional[int] = Field(None, description="Ordering integer")
    is_active: Optional[bool] = Field(False, description="Whether the stage is active")
    school_id: Optional[int] = Field(None, description="Optional school id; derived from actor if omitted")

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        return v.strip()

    @field_validator("code")
    @classmethod
    def _strip_code(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class AcademicStageUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = None
    num_code: Optional[int] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    school_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def _strip_name_optional(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v

    @field_validator("code")
    @classmethod
    def _strip_code_optional(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


class AcademicStageResponse(BaseModel):
    id: int
    name: str
    code: Optional[str]
    num_code: Optional[int]
    display_order: Optional[int]
    is_active: bool
    school_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)
