from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ResultBase(BaseModel):
    student_id: int
    exam_id: int
    marks_obtained: float

    @field_validator("marks_obtained")
    @classmethod
    def marks_not_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("marks_obtained cannot be negative")
        return v


class ResultCreateRequest(ResultBase):
    pass


class ResultResponse(ResultBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)