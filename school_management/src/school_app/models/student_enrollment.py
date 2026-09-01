from datetime import datetime, timezone

from sqlalchemy import Index, text

from school_app.enums.enrollment import EnrollmentStatus
from school_app.extensions import db


def _utcnow():
  """Return the current UTC time."""
  return datetime.now(timezone.utc)


class StudentEnrollment(db.Model):
  """A record of a student's placement in a classroom during an academic session."""

  __tablename__ = "student_enrollments"

  __table_args__ = (
      Index(
          "uq_active_student_enrollment",
          "school_id",
          "student_id",
          "academic_session_id",
          unique=True,
          # Enforce uniqueness only for truly active enrollments.
          # Use the `status` column so historical/status-changed
          # records (e.g. transferred, promoted) do not collide
          # when `withdrawal_date` is left NULL by fixtures.
          sqlite_where=text("status = 'active'"),
          postgresql_where=text("status = 'active'"),
      ),
  )

  id = db.Column(
      db.Integer,
      primary_key=True,
  )

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

  status = db.Column(
      db.Enum(EnrollmentStatus),
      nullable=False,
      default=EnrollmentStatus.ACTIVE,
  )

  enrollment_date = db.Column(
      db.DateTime,
      nullable=False,
      default=_utcnow,
  )

  withdrawal_date = db.Column(
      db.DateTime,
      nullable=True,
  )

  remarks = db.Column(
      db.String(255),
      nullable=True,
  )

  recorded_by = db.Column(
      db.Integer,
      db.ForeignKey("users.id", ondelete="SET NULL"),
      nullable=True,
  )

  created_at = db.Column(
      db.DateTime,
      nullable=False,
      default=_utcnow,
  )

  updated_at = db.Column(
      db.DateTime,
      nullable=False,
      default=_utcnow,
      onupdate=_utcnow,
  )

  # Relationships
  school = db.relationship(
      "School",
      backref=db.backref(
          "student_enrollments",
          lazy="dynamic",
      ),
  )

  student = db.relationship(
      "Student",
      back_populates="enrollments",
  )

  classroom = db.relationship(
      "Classroom",
      foreign_keys=[classroom_id],
  )

  academic_session = db.relationship(
      "AcademicSession",
      foreign_keys=[academic_session_id],
  )

  recorded_by_user = db.relationship(
      "User",
      foreign_keys=[recorded_by],
  )