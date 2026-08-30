from datetime import time
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from school_app.enums.day_of_week import DayOfWeek

class TimetableCreateRequest(BaseModel):
    term_id: int = Field(..., gt=0, description="The ID of the academic term")
    classroom_id: int = Field(..., gt=0, description="The ID of the classroom")
    subject_id: int = Field(..., gt=0, description="The ID of the subject")
    teacher_id: int = Field(..., gt=0, description="The ID of the teacher")
    day_of_week: DayOfWeek
    start_time: time
    end_time: time

    model_config = ConfigDict(from_attributes=True)


class TimetableUpdateRequest(BaseModel):
    term_id: Optional[int] = Field(None, gt=0, description="The ID of the academic term")
    classroom_id: Optional[int] = Field(None, gt=0, description="The ID of the classroom")
    subject_id: Optional[int] = Field(None, gt=0, description="The ID of the subject")
    teacher_id: Optional[int] = Field(None, gt=0, description="The ID of the teacher")
    day_of_week: Optional[DayOfWeek] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    model_config = ConfigDict(from_attributes=True)