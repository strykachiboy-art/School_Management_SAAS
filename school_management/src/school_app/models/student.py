# App/models/student.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.models.association import student_subjects


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class Student(db.Model):
    __tablename__ = "students"
    __table_args__ = (
        db.UniqueConstraint("school_id", "admission_number", name="uq_student_admission_number_per_school"),
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    admission_number = db.Column(db.String(50), nullable=True)  # Scoped via UniqueConstraint
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    current_session_id = db.Column(db.Integer, db.ForeignKey("academic_sessions.id", ondelete="SET NULL"), nullable=True)
    current_term_id = db.Column(db.Integer, db.ForeignKey("terms.id", ondelete="SET NULL"), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    # Relationships
    school = db.relationship("School", backref=db.backref("students", lazy="dynamic"))
    subjects = db.relationship("Subject", back_populates="students", secondary=student_subjects)
    user = db.relationship("User", back_populates="student_profile")
    classroom = db.relationship("Classroom", back_populates="students")
    results = db.relationship("Result", back_populates="student")
    attendance_records = db.relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    promotion_history = db.relationship("PromotionHistory", back_populates="student", cascade="all, delete-orphan")
    enrollments = db.relationship("StudentEnrollment", back_populates="student", cascade="all, delete-orphan")
    current_session = db.relationship("AcademicSession", foreign_keys=[current_session_id])
    current_term = db.relationship("Term", foreign_keys=[current_term_id])