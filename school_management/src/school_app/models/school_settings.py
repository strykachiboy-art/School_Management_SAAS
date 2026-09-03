from datetime import datetime, timezone
from school_app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class SchoolSettings(db.Model):
    __tablename__ = "school_settings"

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), unique=True, nullable=False)

    # --- profile & branding ---
    logo_url = db.Column(db.String(500), nullable=True)
    emblem_url = db.Column(db.String(500), nullable=True)
    motto = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    contact_email = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    primary_color = db.Column(db.String(20), nullable=True)
    secondary_color = db.Column(db.String(20), nullable=True)
    principal_name = db.Column(db.String(150), nullable=True)
    school_stamp_url = db.Column(db.String(500), nullable=True)
    report_header = db.Column(db.Text, nullable=True)
    report_footer = db.Column(db.Text, nullable=True)

    # --- report card display toggles ---
    show_logo_on_report = db.Column(db.Boolean, default=True, nullable=False)
    show_student_photo_on_report = db.Column(db.Boolean, default=True, nullable=False)
    show_grade_on_report = db.Column(db.Boolean, default=True, nullable=False)
    show_attendance_on_report = db.Column(db.Boolean, default=True, nullable=False)
    show_teacher_remarks_on_report = db.Column(db.Boolean, default=True, nullable=False)
    show_principal_remarks_on_report = db.Column(db.Boolean, default=False, nullable=False)
    show_ranking_on_report = db.Column(db.Boolean, default=False, nullable=False)
    enable_class_ranking = db.Column(db.Boolean, default=False, nullable=False)

    # --- result access & PIN security ---
    require_result_pin = db.Column(db.Boolean, default=False, nullable=False)
    result_pin_length = db.Column(db.Integer, default=4, nullable=False)
    public_result_verification_enabled = db.Column(db.Boolean, default=True, nullable=False)

    # --- notification preferences: school-level defaults.
    # Shape: {"RESULT": {"email": true, "in_app": true, "sms": false}, ...}
    # keyed by NotificationType.value. Per-user override is future work.
    notification_preferences = db.Column(db.JSON, default=dict, nullable=False)

    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    school = db.relationship("School", back_populates="settings")

    def __repr__(self):
        return f"<SchoolSettings school_id={self.school_id}>"