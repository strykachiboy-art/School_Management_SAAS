from datetime import datetime, timezone

from school_app.enums.enrollment import EnrollmentStatus
from school_app.extensions import db
from school_app.models.academic_session import AcademicSession
from school_app.models.classroom import Classroom
from school_app.models.student_enrollment import StudentEnrollment


def _utcnow():
  """Return the current UTC time."""
  return datetime.now(timezone.utc)


def _get_current_session_id(school_id=None):
  """Retrieve the active academic session ID, optionally filtered by school."""
  stmt = db.select(AcademicSession).where(
      AcademicSession.is_active.is_(True)
  )

  if school_id is not None:
    stmt = stmt.where(AcademicSession.school_id == school_id)

  session = db.session.scalars(stmt).first()

  return session.id if session else None


def get_current_enrollment(student_id, academic_session_id=None):
  """Fetch a student's active enrollment (where withdrawal_date is NULL)."""
  stmt = db.select(StudentEnrollment).where(
      StudentEnrollment.student_id == student_id,
      StudentEnrollment.withdrawal_date.is_(None),
  )

  if academic_session_id is not None:
    stmt = stmt.where(
        StudentEnrollment.academic_session_id == academic_session_id
    )

  return db.session.scalars(stmt).first()


def get_enrollment_history(student_id):
  """Fetch all enrollment records for a student ordered by most recent first."""
  stmt = (
      db.select(StudentEnrollment)
      .where(StudentEnrollment.student_id == student_id)
      .order_by(
          StudentEnrollment.enrollment_date.desc(),
          StudentEnrollment.id.desc(),
      )
  )

  return db.session.scalars(stmt).all()


def record_enrollment(
    student_id,
    classroom_id,
    academic_session_id=None,
    status=None,
    remarks=None,
    recorded_by=None,
    school_id=None,
):
  """Create a new student enrollment.

  If the student already has a current enrollment in the same
  academic session, that enrollment is closed before the new
  enrollment is created.
  """
  if classroom_id is None:
    return None

  # Resolve school from classroom if not supplied.
  if school_id is None:
    classroom = db.session.get(
        Classroom,
        classroom_id,
    )

    if classroom is None:
      return None

    school_id = classroom.school_id

  if academic_session_id is None:
    academic_session_id = _get_current_session_id(
        school_id=school_id,
    )

  if academic_session_id is None:
    return None

  # Find the student's current enrollment for this session.
  current = get_current_enrollment(
      student_id,
      academic_session_id=academic_session_id,
  )

  if current is not None:
    current.withdrawal_date = _utcnow()
    current.status = (
        status if status is not None else EnrollmentStatus.TRANSFERRED
    )

  new_status = (
      status if status is not None else EnrollmentStatus.ACTIVE
  )

  new_enrollment = StudentEnrollment(
      school_id=school_id,
      student_id=student_id,
      classroom_id=classroom_id,
      academic_session_id=academic_session_id,
      status=new_status,
      remarks=remarks,
      recorded_by=recorded_by,
  )

  db.session.add(new_enrollment)
  db.session.flush()

  return new_enrollment