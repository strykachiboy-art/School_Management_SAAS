from datetime import date, datetime, time
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator

from school_app.enums.assessment import AssessmentType


# Base schema containing shared exam fields
class ExamBase(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: int
    classroom_id: int
    session_id: int
    term_id: Optional[int] = None
    exam_date: date
    start_time: time
    duration_minutes: Optional[int] = None
    total_marks: int
    assessment_type: AssessmentType = AssessmentType.EXAMINATION
    weight: float = 100.0
    is_required: bool = True

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title cannot be blank")
        return v

    @field_validator("exam_date")
    @classmethod
    def exam_date_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("exam_date cannot be in the past")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def duration_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("duration_minutes must be a positive number")
        return v

    @field_validator("total_marks")
    @classmethod
    def total_marks_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("total_marks must be a positive number")
        return v

    @field_validator("weight")
    @classmethod
    def weight_in_range(cls, v: float) -> float:
        # Weight is a percentage contribution to the subject's period score.
        if v < 0 or v > 100:
            raise ValueError("weight must be between 0 and 100")
        return v


# Schema used for creating an exam
class ExamCreateRequest(ExamBase):
    pass


# Schema used for updating an exam — every field optional so a partial
# PATCH-style update only changes what's provided.
class ExamUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    subject_id: Optional[int] = None
    classroom_id: Optional[int] = None
    session_id: Optional[int] = None
    term_id: Optional[int] = None
    exam_date: Optional[date] = None
    start_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    total_marks: Optional[int] = None
    assessment_type: Optional[AssessmentType] = None
    weight: Optional[float] = None
    is_required: Optional[bool] = None


# Schema used for serializing exam data in API responses (equivalent to dump_only fields)
class ExamResponse(ExamBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)