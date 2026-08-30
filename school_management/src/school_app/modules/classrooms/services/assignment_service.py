from school_app.extensions import db
from school_app.models.subject import Subject
from school_app.models.teacher import Teacher
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction

MAX_TEACHERS_PER_ASSIGNMENT = 500
MAX_STUDENTS_PER_ASSIGNMENT = 500
MAX_CLASSROOMS_PER_ASSIGNMENT = 500


# ================================ Generic helpers ==================================
def _get_subject_or_raise(subject_id):
    subject = db.session.get(Subject, subject_id)
    if not subject:
        raise ValueError(f"Subject with ID {subject_id} does not exist.")
    return subject


def _fetch_and_validate(model, ids, max_allowed, label):
    ids = list(set(ids))  # dedupe

    if len(ids) > max_allowed:
        raise ValueError(
            f"Too many {label} IDs in one request ({len(ids)}). "
            f"Max is {max_allowed} — split into smaller batches."
        )

    stmt = db.select(model).where(model.id.in_(ids))
    records = db.session.scalars(stmt).all()

    found_ids = {r.id for r in records}
    missing_ids = set(ids) - found_ids
    if missing_ids:
        raise ValueError(f"{label.capitalize()} IDs not found: {sorted(missing_ids)}")

    return records


def _assign_subject_to(model, subject_id, record_ids, max_allowed, label, actor_id):
    subject = _get_subject_or_raise(subject_id)
    records = _fetch_and_validate(model, record_ids, max_allowed, label)

    assigned_records = []
    for record in records:
        # Check if already assigned — raise ValueError to trigger 400 response
        if subject in record.subjects:
            raise ValueError(f"Subject is already assigned to this {label}")
        
        record.subjects.append(subject)
        assigned_records.append(record)


    if assigned_records and actor_id:
        record_ids_list = [r.id for r in assigned_records]
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=f"Assigned subject {subject.name} to {len(assigned_records)} {label}(s)",
            changes={f"assigned_{label}_ids": {"added": record_ids_list}}
        )
        
    db.session.commit()


def _remove_subject_from(model, subject_id, record_ids, max_allowed, label, actor_id):
    subject = _get_subject_or_raise(subject_id)
    records = _fetch_and_validate(model, record_ids, max_allowed, label)

    removed_records = []
    for record in records:
        if subject in record.subjects:
            record.subjects.remove(subject)
            removed_records.append(record)


    if removed_records and actor_id:
        record_ids_list = [r.id for r in removed_records]
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=f"Removed subject {subject.name} from {len(removed_records)} {label}(s)",
            changes={f"removed_{label}_ids": {"removed": record_ids_list}}
        )
        
    db.session.commit()


def _get_subjects_for(model, record_id, label):
    record = db.session.get(model, record_id)
    if not record:
        raise ValueError(f"{label.capitalize()} with ID {record_id} does not exist.")
    return record.subjects


# ================================ Teacher assignment ==================================
def assign_subject_to_teachers(subject_id, teacher_ids, actor_id=None):
    _assign_subject_to(Teacher, subject_id, teacher_ids, MAX_TEACHERS_PER_ASSIGNMENT, "teacher", actor_id)

def remove_subject_from_teachers(subject_id, teacher_ids, actor_id=None):
    _remove_subject_from(Teacher, subject_id, teacher_ids, MAX_TEACHERS_PER_ASSIGNMENT, "teacher", actor_id)

def get_subjects_for_teacher(teacher_id):
    return _get_subjects_for(Teacher, teacher_id, "teacher")


# ================================ Student assignment ==================================
def assign_subject_to_students(subject_id, student_ids, actor_id=None):
    _assign_subject_to(Student, subject_id, student_ids, MAX_STUDENTS_PER_ASSIGNMENT, "student", actor_id)

def remove_subject_from_students(subject_id, student_ids, actor_id=None):
    _remove_subject_from(Student, subject_id, student_ids, MAX_STUDENTS_PER_ASSIGNMENT, "student", actor_id)

def get_subjects_for_student(student_id):
    return _get_subjects_for(Student, student_id, "student")


# ================================ Classroom assignment ==================================
def assign_subject_to_classrooms(subject_id, classroom_ids, actor_id=None):
    _assign_subject_to(Classroom, subject_id, classroom_ids, MAX_CLASSROOMS_PER_ASSIGNMENT, "classroom", actor_id)

def remove_subject_from_classrooms(subject_id, classroom_ids, actor_id=None):
    _remove_subject_from(Classroom, subject_id, classroom_ids, MAX_CLASSROOMS_PER_ASSIGNMENT, "classroom", actor_id)

def get_subjects_for_classroom(classroom_id):
    return _get_subjects_for(Classroom, classroom_id, "classroom")