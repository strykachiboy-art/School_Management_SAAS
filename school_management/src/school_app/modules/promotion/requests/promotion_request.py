from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from school_app.enums.promotion import PromotionDecision


# ====================================== evaluate_student_promotion ===============================================

class PromotionEvaluationResponse(BaseModel):
    student_id: int
    academic_session_id: int
    average_score: float
    attendance_percentage: float
    recommendation: PromotionDecision
    model_config = ConfigDict(from_attributes=True)


# ====================================== promote_student ===============================================

class PromoteStudentRequest(BaseModel):
    to_classroom_id: int
    remarks: Optional[str] = None
    allow_level_skip: bool = False


# ====================================== repeat_student ===============================================

class RepeatStudentRequest(BaseModel):
    remarks: Optional[str] = None


# ====================================== graduate_student ===============================================

class GraduateStudentRequest(BaseModel):
    remarks: Optional[str] = None


# ====================================== bulk promote_session ===============================================

class BulkPromoteRequest(BaseModel):
    classroom_id: Optional[int] = None  # omit to bulk-promote the whole session


class BulkPromoteResponse(BaseModel):
    promoted: list[int]
    repeated: list[int]
    graduated: list[int]
    skipped: list[dict]


# ====================================== PromotionHistory response ===============================================

class PromotionHistoryResponse(BaseModel):
    id: int
    student_id: int
    academic_session_id: int
    from_classroom_id: Optional[int] = None
    to_classroom_id: Optional[int] = None
    decision: PromotionDecision
    average_score: Optional[float] = None
    attendance_percentage: Optional[float] = None
    remarks: Optional[str] = None
    decided_by: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)