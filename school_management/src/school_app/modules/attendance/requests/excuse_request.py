from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from school_app.enums.excuse import ExcuseStatus


class ExcuseCreateRequest(BaseModel):
    attendance_id: int = Field(..., gt=0, description="ID of the attendance record being excused")
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for the absence")


class ExcuseUpdateRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500, description="Updated reason for the absence")


class BulkExcuseReviewRequest(BaseModel):
    excuse_ids: list[int] = Field(..., min_length=1, description="IDs of excuses to approve or reject")


class ExcuseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    attendance_id: int
    reason: str
    status: ExcuseStatus
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime