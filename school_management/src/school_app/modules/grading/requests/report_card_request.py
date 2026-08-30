from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field
from school_app.enums.reportcard import ReportCardStatus


class ReportCardCalculateRequest(BaseModel):
    student_id: int
    academic_session_id: int
    term_id: int


class ReportCardStatusUpdateRequest(BaseModel):
    status: ReportCardStatus


class ReportCardSetPinRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=10)


class ReportCardPublicVerifyRequest(BaseModel):
    reference: str
    pin: Optional[str] = None


class ReportCardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    academic_session_id: int
    term_id: int
    status: ReportCardStatus
    public_reference: str
    summary_data: Optional[Dict[str, Any]] = None