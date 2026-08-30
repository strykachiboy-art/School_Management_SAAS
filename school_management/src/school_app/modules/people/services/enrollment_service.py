from datetime import datetime, timezone

from school_app.extensions import db
from school_app.models.student_enrollment import StudentEnrollment
from school_app.models.academic_session import AcademicSession
from school_app.enums.enrollment import EnrollmentStatus


def _utcnow():
    return datetime.now(timezone.utc)


def _get_current_session_id(school_id=None):
 
    stmt = db.select(AcademicSession).where(AcademicSession.is_active.is_(True))
    if school_id is not None:
        stmt = stmt.where(AcademicSession.school_id == school_id)
    session = db.session.scalars(stmt).first()
    return session.id if session else None


def get_current_enrollment(student_id):
    stmt = db.select(StudentEnrollment).where(
        StudentEnrollment.student_id == student_id, StudentEnrollment.withdrawal_date.is_(None)
    )
    return db.session.scalars(stmt).first()


def get_enrollment_history(student_id):
    stmt = (
        db.select(StudentEnrollment)
        .where(StudentEnrollment.student_id == student_id)
        .order_by(StudentEnrollment.enrollment_date.desc())
    )
    return db.session.scalars(stmt).all()


def record_enrollment(student_id, classroom_id, academic_session_id=None, status=None, remarks=None, recorded_by=None, school_id=None):
   
    if academic_session_id is None:
        academic_session_id = _get_current_session_id(school_id=school_id)

    current = get_current_enrollment(student_id)

    if current is not None:
        current.withdrawal_date = _utcnow()
        if status is not None:

            current.status = status
        elif classroom_id is None:
            current.status = EnrollmentStatus.WITHDRAWN
        else:
            current.status = EnrollmentStatus.TRANSFERRED

    if classroom_id is None:
        return None

    if academic_session_id is None:
        return None

    new_enrollment = StudentEnrollment(
        student_id=student_id,
        classroom_id=classroom_id,
        academic_session_id=academic_session_id,
        status=EnrollmentStatus.ACTIVE,
        remarks=remarks,
        recorded_by=recorded_by,
    )
    db.session.add(new_enrollment)
    db.session.flush()

    return new_enrollment