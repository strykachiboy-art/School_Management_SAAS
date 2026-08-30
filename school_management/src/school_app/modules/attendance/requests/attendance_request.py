from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, field_validator
from school_app.enums.attendance import AttendanceStatus


# Schema for an individual student's record in the bulk payload
class StudentAttendanceRecord(BaseModel):
    student_id: int
    status: AttendanceStatus


# Schema for the bulk classroom attendance request
class MarkClassroomAttendanceRequest(BaseModel):
    term_id: int
    date: date
    attendance_data: List[StudentAttendanceRecord]


# Base schema containing shared attendance fields
class AttendanceBase(BaseModel):
    student_id: int
    term_id: int
    date: date
    status: AttendanceStatus


# Schema used for creating a new attendance record
class AttendanceCreateRequest(AttendanceBase):
    pass


# Schema used for updating an existing attendance record (all fields optional)
class AttendanceUpdateRequest(BaseModel):
    student_id: Optional[int] = None
    term_id: Optional[int] = None
    date: Optional[date] = None
    status: Optional[AttendanceStatus] = None


# Schema used for serializing attendance data in API responses
class AttendanceResponse(AttendanceBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)