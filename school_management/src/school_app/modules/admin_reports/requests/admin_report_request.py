from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, model_validator

MAX_PAGE_SIZE = 200
DEFAULT_PAGE_SIZE = 50


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)


class DateRangeParams(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def end_not_before_start(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class AcademicReportFilters(BaseModel):
    session_id: Optional[int] = None
    classroom_id: Optional[int] = None
    subject_id: Optional[int] = None


class AttendanceReportFilters(DateRangeParams, PaginationParams):
    session_id: Optional[int] = None
    term_id: Optional[int] = None
    classroom_id: Optional[int] = None
    student_id: Optional[int] = None


class ClassroomsReportFilters(BaseModel):
    session_id: Optional[int] = None
    term_id: Optional[int] = None


class StudentsReportFilters(DateRangeParams, PaginationParams):
    classroom_id: Optional[int] = None
    gender: Optional[str] = None
    session_id: Optional[int] = None
    term_id: Optional[int] = None
    is_active: Optional[bool] = None


class TeachersReportFilters(BaseModel):
    gender: Optional[str] = None
    subject_id: Optional[int] = None
    classroom_id: Optional[int] = None
    is_active: Optional[bool] = None


class FeesReportFilters(DateRangeParams):
    session_id: Optional[int] = None
    term_id: Optional[int] = None
    classroom_id: Optional[int] = None
    student_id: Optional[int] = None