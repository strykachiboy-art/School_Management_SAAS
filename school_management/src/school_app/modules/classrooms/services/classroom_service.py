from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.classroom import Classroom
from school_app.models.student import Student
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def create_classroom(data, actor_id=None):
    classroom = Classroom(
        name=data.name,
        capacity=data.capacity or 0,
        location=data.location,
        teacher_id=data.teacher_id or None,
    )

    db.session.add(classroom)

    try:
        db.session.flush() 
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create classroom — check for duplicate name.")

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Classroom",
            resource_id=classroom.id,
            description=f"Created classroom {classroom.name}",
        )

    db.session.commit()

    return classroom


def get_all_classrooms(search="", page=1, per_page=10):
    stmt = db.select(Classroom)
    if search:
        stmt = stmt.where(Classroom.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(Classroom.id.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_classroom(classroom_id):
    return db.session.get(Classroom, classroom_id)


def get_all_classroom_list():
    stmt = db.select(Classroom).order_by(Classroom.id.desc())
    return db.session.scalars(stmt).all()


def update_classroom(classroom_id, data, actor_id=None):
    classroom = db.session.get(Classroom, classroom_id)
    if classroom is None:
        return None

    changes = {}
    if data.name and data.name != classroom.name:
        changes["name"] = {"before": classroom.name, "after": data.name}
    if data.capacity is not None and data.capacity != classroom.capacity:
        changes["capacity"] = {"before": classroom.capacity, "after": data.capacity}
    if data.location and data.location != classroom.location:
        changes["location"] = {"before": classroom.location, "after": data.location}
    if data.teacher_id is not None and data.teacher_id != classroom.teacher_id:
        changes["teacher_id"] = {"before": classroom.teacher_id, "after": data.teacher_id}

    classroom.name = data.name or classroom.name
    classroom.capacity = data.capacity if data.capacity is not None else classroom.capacity
    classroom.location = data.location or classroom.location

    if data.teacher_id is not None:
        classroom.teacher_id = data.teacher_id or None

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update classroom — check for duplicate name.")

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Classroom",
            resource_id=classroom.id,
            description=f"Updated classroom {classroom.name}",
            changes=changes,
        )

    db.session.commit()

    return classroom


def delete_classroom(classroom_id, actor_id=None):
    classroom = db.session.get(Classroom, classroom_id)
    if classroom is None:
        return False

    classroom_name = classroom.name
    db.session.delete(classroom)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Classroom",
            resource_id=classroom_id,
            description=f"Deleted classroom {classroom_name}",
        )

    db.session.commit()

    return True


def bulk_assign_students(classroom_id, student_ids, actor_id=None):
    classroom = db.session.get(Classroom, classroom_id)
    if classroom is None:
        return None

    stmt = db.select(Student).where(Student.id.in_(student_ids))
    students = db.session.scalars(stmt).all()

    found_ids = {s.id for s in students}
    missing_ids = [sid for sid in student_ids if sid not in found_ids]

    for student in students:
        student.classroom_id = classroom.id

    db.session.flush()

    if actor_id and found_ids:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.BULK_ACTION,
            resource_type="Classroom",
            resource_id=classroom.id,
            description=f"Bulk assigned {len(found_ids)} student(s) to classroom {classroom.name}",
            changes={"assigned_student_ids": sorted(list(found_ids))}
        )

    db.session.commit()

    return {
        "classroom_id": classroom.id,
        "assigned_ids": sorted(found_ids),
        "missing_ids": missing_ids,
    }


def serialize_classroom(classroom):
    return {
        "id": classroom.id,
        "name": classroom.name,
        "capacity": classroom.capacity,
        "location": classroom.location,
        "teacher_id": classroom.teacher_id,
    }