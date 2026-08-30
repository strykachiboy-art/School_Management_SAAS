# App/models/report_card.py

import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from school_app.extensions import db
from school_app.enums.reportcard import ReportCardStatus


def _utcnow():
    return datetime.now(timezone.utc)


class ReportCard(db.Model):
    __tablename__ = "report_cards"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "student_id", "academic_session_id", "term_id",
            name="uq_student_report_card_per_term_per_school",
        ), {"extend_existing": True}
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    academic_session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    term_id = db.Column(
        db.Integer,
        db.ForeignKey("terms.id", ondelete="CASCADE"),
        nullable=False,
    )

    status = db.Column(
        db.Enum(ReportCardStatus),
        default=ReportCardStatus.DRAFT,
        nullable=False,
    )

    # Opaque, non-sequential reference string for public/external access (kept globally unique)
    public_reference = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Secure hash for verification access pin
    access_pin_hash = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("report_cards", lazy="dynamic"))
    student = db.relationship("Student", backref=db.backref("report_cards", lazy="dynamic"))
    academic_session = db.relationship("AcademicSession")
    term = db.relationship("Term")

    def __init__(self, **kwargs):
        super(ReportCard, self).__init__(**kwargs)
        if not self.public_reference:
            self.public_reference = secrets.token_urlsafe(16)

    def set_access_pin(self, pin: str):
        self.access_pin_hash = generate_password_hash(pin)

    def check_access_pin(self, pin: str) -> bool:
        if not self.access_pin_hash:
            return False
        return check_password_hash(self.access_pin_hash, pin)