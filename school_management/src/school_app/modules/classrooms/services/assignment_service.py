from school_app.extensions import db
from school_app.models.subject import Subject
from school_app.models.teacher import Teacher
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.models.association import (
    teacher_subjects,
    student_subjects,
    classroom_subjects,
)
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


MAX_TEACHERS_PER_ASSIGNMENT = 500
MAX_STUDENTS_PER_ASSIGNMENT = 500
MAX_CLASSROOMS_PER_ASSIGNMENT = 500


# ================================ Association mapping ================================

ASSOCIATION_TABLES = {
    Teacher: teacher_subjects,
    Student: student_subjects,
    Classroom: classroom_subjects,
}


ASSOCIATION_ID_COLUMNS = {
    Teacher: teacher_subjects.c.teacher_id,
    Student: student_subjects.c.student_id,
    Classroom: classroom_subjects.c.classroom_id,
}


# ================================ Generic helpers ==================================

def _get_subject_or_raise(subject_id):
    subject = db.session.get(Subject, subject_id)

    if not subject:
        raise ValueError(f"Subject with ID {subject_id} does not exist.")

    return subject


def _fetch_and_validate(model, ids, max_allowed, label):
    ids = list(set(ids))

    if len(ids) > max_allowed:
        raise ValueError(
            f"Too many {label} IDs in one request ({len(ids)}). "
            f"Max is {max_allowed} — split into smaller batches."
        )

    stmt = db.select(model).where(model.id.in_(ids))
    records = db.session.scalars(stmt).all()

    found_ids = {record.id for record in records}
    missing_ids = set(ids) - found_ids

    if missing_ids:
        raise ValueError(
            f"{label.capitalize()} IDs not found: {sorted(missing_ids)}"
        )

    return records


def _get_association_table(model):
    try:
        return ASSOCIATION_TABLES[model]
    except KeyError:
        raise ValueError(
            f"No subject association table configured for {model.__name__}."
        )


def _get_association_id_column(model):
    try:
        return ASSOCIATION_ID_COLUMNS[model]
    except KeyError:
        raise ValueError(
            f"No subject association ID column configured for {model.__name__}."
        )


def _is_subject_assigned(model, record_id, subject_id):
    association_table = _get_association_table(model)
    id_column = _get_association_id_column(model)

    stmt = db.select(association_table.c.school_id).where(
        id_column == record_id,
        association_table.c.subject_id == subject_id,
    )

    return db.session.execute(stmt).first() is not None


def _assign_subject_to(
    model,
    subject_id,
    record_ids,
    max_allowed,
    label,
    actor_id,
):
    subject = _get_subject_or_raise(subject_id)

    records = _fetch_and_validate(
        model,
        record_ids,
        max_allowed,
        label,
    )

    association_table = _get_association_table(model)
    id_column = _get_association_id_column(model)

    assigned_records = []

    for record in records:
        if _is_subject_assigned(model, record.id, subject.id):
            raise ValueError(
                f"Subject is already assigned to this {label}"
            )

        if not record.school_id:
            raise ValueError(
                f"{label.capitalize()} {record.id} is not associated with a school."
            )

        if not subject.school_id:
            raise ValueError(
                f"Subject {subject.id} is not associated with a school."
            )

        if record.school_id != subject.school_id:
            raise ValueError(
                f"Cannot assign subject from school {subject.school_id} "
                f"to {label} from school {record.school_id}."
            )

        db.session.execute(
            association_table.insert().values(
                school_id=record.school_id,
                **{
                    id_column.name: record.id,
                },
                subject_id=subject.id,
            )
        )

        assigned_records.append(record)

    if assigned_records and actor_id:
        record_ids_list = [
            record.id for record in assigned_records
        ]

        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=(
                f"Assigned subject {subject.name} to "
                f"{len(assigned_records)} {label}(s)"
            ),
            changes={
                f"assigned_{label}_ids": {
                    "added": record_ids_list
                }
            },
        )

    db.session.commit()


def _remove_subject_from(
    model,
    subject_id,
    record_ids,
    max_allowed,
    label,
    actor_id,
):
    subject = _get_subject_or_raise(subject_id)

    records = _fetch_and_validate(
        model,
        record_ids,
        max_allowed,
        label,
    )

    association_table = _get_association_table(model)
    id_column = _get_association_id_column(model)

    removed_records = []

    for record in records:
        if _is_subject_assigned(model, record.id, subject.id):
            db.session.execute(
                association_table.delete().where(
                    id_column == record.id,
                    association_table.c.subject_id == subject.id,
                )
            )

            removed_records.append(record)

    if removed_records and actor_id:
        record_ids_list = [
            record.id for record in removed_records
        ]

        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=(
                f"Removed subject {subject.name} from "
                f"{len(removed_records)} {label}(s)"
            ),
            changes={
                f"removed_{label}_ids": {
                    "removed": record_ids_list
                }
            },
        )

    db.session.commit()


def _get_subjects_for(model, record_id, label):
    record = db.session.get(model, record_id)

    if not record:
        raise ValueError(
            f"{label.capitalize()} with ID {record_id} does not exist."
        )

    return record.subjects


# ================================ Teacher assignment ==================================

def assign_subject_to_teachers(
    subject_id,
    teacher_ids,
    actor_id=None,
):
    _assign_subject_to(
        Teacher,
        subject_id,
        teacher_ids,
        MAX_TEACHERS_PER_ASSIGNMENT,
        "teacher",
        actor_id,
    )


def remove_subject_from_teachers(
    subject_id,
    teacher_ids,
    actor_id=None,
):
    _remove_subject_from(
        Teacher,
        subject_id,
        teacher_ids,
        MAX_TEACHERS_PER_ASSIGNMENT,
        "teacher",
        actor_id,
    )


def get_subjects_for_teacher(teacher_id):
    return _get_subjects_for(
        Teacher,
        teacher_id,
        "teacher",
    )


# ================================ Student assignment ==================================

def assign_subject_to_students(
    subject_id,
    student_ids,
    actor_id=None,
):
    _assign_subject_to(
        Student,
        subject_id,
        student_ids,
        MAX_STUDENTS_PER_ASSIGNMENT,
        "student",
        actor_id,
    )


def remove_subject_from_students(
    subject_id,
    student_ids,
    actor_id=None,
):
    _remove_subject_from(
        Student,
        subject_id,
        student_ids,
        MAX_STUDENTS_PER_ASSIGNMENT,
        "student",
        actor_id,
    )


def get_subjects_for_student(student_id):
    return _get_subjects_for(
        Student,
        student_id,
        "student",
    )


# ================================ Classroom assignment ==================================

def assign_subject_to_classrooms(
    subject_id,
    classroom_ids,
    actor_id=None,
):
    _assign_subject_to(
        Classroom,
        subject_id,
        classroom_ids,
        MAX_CLASSROOMS_PER_ASSIGNMENT,
        "classroom",
        actor_id,
    )


def remove_subject_from_classrooms(
    subject_id,
    classroom_ids,
    actor_id=None,
):
    _remove_subject_from(
        Classroom,
        subject_id,
        classroom_ids,
        MAX_CLASSROOMS_PER_ASSIGNMENT,
        "classroom",
        actor_id,
    )


def get_subjects_for_classroom(classroom_id):
    return _get_subjects_for(
        Classroom,
        classroom_id,
        "classroom",
    )