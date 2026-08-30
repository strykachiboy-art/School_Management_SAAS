from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class GradingRuleBase(BaseModel):
    grading_system_id: int
    grade_name: str = Field(..., min_length=1, max_length=20)
    min_score: float = Field(..., ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    grade_point: Optional[float] = None
    remark: Optional[str] = Field(None, max_length=100)
    display_order: int = 0

    @field_validator("max_score")
    @classmethod
    def max_not_below_min(cls, v, info):
        min_score = info.data.get("min_score")
        if v is not None and min_score is not None and v < min_score:
            raise ValueError("max_score cannot be less than min_score")
        return v


class GradingRuleCreateRequest(GradingRuleBase):
    pass


class GradingRuleUpdateRequest(BaseModel):
    grade_name: Optional[str] = Field(None, min_length=1, max_length=20)
    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    grade_point: Optional[float] = None
    remark: Optional[str] = Field(None, max_length=100)
    display_order: Optional[int] = None


class GradingRuleResponse(GradingRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)