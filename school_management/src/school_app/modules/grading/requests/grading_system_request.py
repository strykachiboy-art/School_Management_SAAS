from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from school_app.enums.grading import GradingStrategy


class GradingSystemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    strategy: GradingStrategy = GradingStrategy.LETTER_GRADE
    is_default: bool = False
    school_id: Optional[int] = None


class GradingSystemCreateRequest(GradingSystemBase):
    pass


class GradingSystemUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    strategy: Optional[GradingStrategy] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class GradingSystemResponse(GradingSystemBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)