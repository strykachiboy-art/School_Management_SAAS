from flask import abort
from school_app.models.exam import Exam
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction

# ================================== Create Exam ===============================
def create_exam(data, school_id, actor_id=None):
    """data is an ExamCreateRequest (Pydantic) — build the Exam model here."""
    exam = Exam(
        school_id=school_id,
        title=data.title,
        description=data.description,
        subject_id=data.subject_id,
        classroom_id=data.classroom_id,
        session_id=data.session_id,
        term_id=data.term_id,
        exam_date=data.exam_date,
        start_time=data.start_time,
        duration_minutes=data.duration_minutes,
        total_marks=data.total_marks,
        assessment_type=data.assessment_type,
        weight=data.weight,
        is_required=data.is_required,
    )

    db.session.add(exam)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create exam — check for duplicate entries or constraints.")

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Exam",
            resource_id=exam.id,
            description=f"Created exam {exam.title}",
        )

    db.session.commit()

    return exam

# =============================== Get exam_id ================================
def get_exam(exam_id, school_id):
    exam = db.session.get(Exam, exam_id)
    if exam is None or exam.school_id != school_id:
        return None
    return exam


# ============================ Get all Exam ==================================
def get_all_exam(school_id):
    return db.session.execute(
        db.select(Exam).where(Exam.school_id == school_id)
    ).scalars().all()


# ============================== Update Exam ===================================
def update_exam(exam_id, form, school_id, actor_id=None):
    """form is an ExamUpdateRequest — every field is Optional[...] = None,
    so "not provided" is unambiguously None and doesn't get confused with a
    genuinely-provided False or 0.
    """
    exam = get_exam(exam_id, school_id)

    if exam is None:
        return None

    changes = {}
    if form.title is not None and form.title != exam.title:
        changes["title"] = {"before": exam.title, "after": form.title}
    if form.description is not None and form.description != exam.description:
        changes["description"] = {"before": exam.description, "after": form.description}
    if form.subject_id is not None and form.subject_id != exam.subject_id:
        changes["subject_id"] = {"before": exam.subject_id, "after": form.subject_id}
    if form.classroom_id is not None and form.classroom_id != exam.classroom_id:
        changes["classroom_id"] = {"before": exam.classroom_id, "after": form.classroom_id}
    if form.session_id is not None and form.session_id != exam.session_id:
        changes["session_id"] = {"before": exam.session_id, "after": form.session_id}
    if form.exam_date is not None and form.exam_date != exam.exam_date:
        changes["exam_date"] = {"before": str(exam.exam_date), "after": str(form.exam_date)}
    if form.start_time is not None and form.start_time != exam.start_time:
        changes["start_time"] = {"before": str(exam.start_time), "after": str(form.start_time)}
    if form.duration_minutes is not None and form.duration_minutes != exam.duration_minutes:
        changes["duration_minutes"] = {"before": exam.duration_minutes, "after": form.duration_minutes}
    if form.total_marks is not None and form.total_marks != exam.total_marks:
        changes["total_marks"] = {"before": exam.total_marks, "after": form.total_marks}
    if form.term_id is not None and form.term_id != exam.term_id:
        changes["term_id"] = {"before": exam.term_id, "after": form.term_id}
    if form.assessment_type is not None and form.assessment_type != exam.assessment_type:
        changes["assessment_type"] = {"before": exam.assessment_type, "after": form.assessment_type}
    if form.weight is not None and form.weight != exam.weight:
        changes["weight"] = {"before": exam.weight, "after": form.weight}
    if form.is_required is not None and form.is_required != exam.is_required:
        changes["is_required"] = {"before": exam.is_required, "after": form.is_required}

    exam.title = form.title if form.title is not None else exam.title
    exam.description = form.description if form.description is not None else exam.description
    exam.subject_id = form.subject_id if form.subject_id is not None else exam.subject_id
    exam.classroom_id = form.classroom_id if form.classroom_id is not None else exam.classroom_id
    exam.session_id = form.session_id if form.session_id is not None else exam.session_id
    exam.exam_date = form.exam_date if form.exam_date is not None else exam.exam_date
    exam.start_time = form.start_time if form.start_time is not None else exam.start_time
    exam.duration_minutes = form.duration_minutes if form.duration_minutes is not None else exam.duration_minutes
    exam.total_marks = form.total_marks if form.total_marks is not None else exam.total_marks
    exam.term_id = form.term_id if form.term_id is not None else exam.term_id
    exam.assessment_type = form.assessment_type if form.assessment_type is not None else exam.assessment_type
    exam.weight = form.weight if form.weight is not None else exam.weight
    exam.is_required = form.is_required if form.is_required is not None else exam.is_required

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Exam",
            resource_id=exam.id,
            description=f"Updated exam {exam.title}",
            changes=changes,
        )

    db.session.commit()

    return exam

# ============================ Delete Exam ===============================
def delete_exam(exam_id, school_id, actor_id=None):
    exam = get_exam(exam_id, school_id)

    if exam is None:
        return False

    exam_title = exam.title
    db.session.delete(exam)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Exam",
            resource_id=exam_id,
            description=f"Deleted exam {exam_title}",
        )

    db.session.commit()

    return True


# =========================== Search and filter ============================
def search_exams(school_id, search=None, subject_id=None, classroom_id=None):
    statement = db.select(Exam).where(Exam.school_id == school_id)

    if search:
        statement = statement.where(
            Exam.title.ilike(f"%{search}%")
        )

    if subject_id:
        statement = statement.where(
            Exam.subject_id == subject_id
        )

    if classroom_id:
        statement = statement.where(
            Exam.classroom_id == classroom_id
        )

    return db.session.execute(statement).scalars().all()


# ========================= paginate_exams ============================
def paginate_exams(school_id, page=1, per_page=20):
    statement = db.select(Exam).where(Exam.school_id == school_id).order_by(Exam.exam_date)

    return db.paginate(statement,
                       page=page,
                       per_page=per_page,
                       error_out=False)