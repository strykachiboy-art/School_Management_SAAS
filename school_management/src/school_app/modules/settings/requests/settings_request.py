from typing import Optional, Dict
from pydantic import BaseModel, Field, ConfigDict


class BrandingSettingsRequest(BaseModel):
    logo_url: Optional[str] = Field(None, max_length=500)
    emblem_url: Optional[str] = Field(None, max_length=500)
    motto: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    address: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    contact_email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)
    primary_color: Optional[str] = Field(None, max_length=20)
    secondary_color: Optional[str] = Field(None, max_length=20)
    principal_name: Optional[str] = Field(None, max_length=150)
    school_stamp_url: Optional[str] = Field(None, max_length=500)
    report_header: Optional[str] = None
    report_footer: Optional[str] = None


class ReportCardSettingsRequest(BaseModel):
    show_logo_on_report: Optional[bool] = None
    show_student_photo_on_report: Optional[bool] = None
    show_grade_on_report: Optional[bool] = None
    show_attendance_on_report: Optional[bool] = None
    show_teacher_remarks_on_report: Optional[bool] = None
    show_principal_remarks_on_report: Optional[bool] = None
    show_ranking_on_report: Optional[bool] = None
    enable_class_ranking: Optional[bool] = None


class ResultAccessSettingsRequest(BaseModel):
    require_result_pin: Optional[bool] = None
    result_pin_length: Optional[int] = Field(None, ge=4, le=10)
    public_result_verification_enabled: Optional[bool] = None


class NotificationPreferencesRequest(BaseModel):
    preferences: Dict[str, Dict[str, bool]] = Field(
        ..., description="Keyed by NotificationType value, e.g. {'RESULT': {'email': true}}"
    )


class SchoolSettingsResponse(BaseModel):
    school_id: int
    logo_url: Optional[str] = None
    emblem_url: Optional[str] = None
    motto: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    principal_name: Optional[str] = None
    school_stamp_url: Optional[str] = None
    report_header: Optional[str] = None
    report_footer: Optional[str] = None
    show_logo_on_report: bool
    show_student_photo_on_report: bool
    show_grade_on_report: bool
    show_attendance_on_report: bool
    show_teacher_remarks_on_report: bool
    show_principal_remarks_on_report: bool
    show_ranking_on_report: bool
    enable_class_ranking: bool
    require_result_pin: bool
    result_pin_length: int
    public_result_verification_enabled: bool
    notification_preferences: Dict[str, Dict[str, bool]]

    model_config = ConfigDict(from_attributes=True)