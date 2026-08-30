from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PromotionRuleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    from_level_id: int
    to_level_id: Optional[int] = None  
    min_average_score: Optional[float] = Field(None, ge=0, le=100)
    min_attendance_percentage: Optional[float] = Field(None, ge=0, le=100)
    min_subject_score: Optional[float] = Field(None, ge=0, le=100)
    max_failed_subjects: Optional[int] = Field(None, ge=0)
    requires_admin_approval: bool = False
    is_active: bool = True


class PromotionRuleCreateRequest(PromotionRuleBase):
    pass


class PromotionRuleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    to_level_id: Optional[int] = None
    min_average_score: Optional[float] = Field(None, ge=0, le=100)
    min_attendance_percentage: Optional[float] = Field(None, ge=0, le=100)
    min_subject_score: Optional[float] = Field(None, ge=0, le=100)
    max_failed_subjects: Optional[int] = Field(None, ge=0)
    requires_admin_approval: Optional[bool] = None
    is_active: Optional[bool] = None


class PromotionRuleResponse(PromotionRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)