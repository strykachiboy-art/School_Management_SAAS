# App/models/student_enrollment.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.enrollment import EnrollmentStatus


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class StudentEnrollment(db.Model):
    """A record of a student's placement in a classroom during an academic
    session.
    """

    __tablename__ = "student_enrollments"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "student_id", "academic_session_id",
            name="uq_student_enrollment_per_session_per_school",
        ), {"extend_existing": True},
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
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="SET NULL"),
        nullable=True,
    )
    academic_session_id = db.Column(
        db.Integer,
        db.ForeignKey("academic_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = db.Column(db.Enum(EnrollmentStatus), nullable=False, default=EnrollmentStatus.ACTIVE)
    enrollment_date = db.Column(db.DateTime, nullable=False, default=_utcnow)
    withdrawal_date = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.String(255), nullable=True)
    recorded_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("student_enrollments", lazy="dynamic"))
    student = db.relationship("Student", back_populates="enrollments")
    classroom = db.relationship("Classroom", foreign_keys=[classroom_id])
    academic_session = db.relationship("AcademicSession", foreign_keys=[academic_session_id])
    recorded_by_user = db.relationship("User", foreign_keys=[recorded_by])