from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.classroom import Classroom
from school_app.models.student import Student
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ 1. Create Classroom ============================

def create_classroom(data, school_id, actor_id=None):
    """
    Create a classroom within a specific school.
    """

    classroom = Classroom(
        school_id=school_id,
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
        abort(
            400,
            description="Could not create classroom — check for duplicate name."
        )

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Classroom",
            resource_id=classroom.id,
            description=f"Created classroom {classroom.name}",
            school_id=school_id,
        )

    db.session.commit()

    return classroom


# ============================ 2. Get All Classrooms ============================

def get_all_classrooms(
    school_id,
    search="",
    page=1,
    per_page=10,
):
    """
    Get paginated classrooms belonging only to the specified school.
    """

    stmt = db.select(Classroom).where(
        Classroom.school_id == school_id
    )

    if search:
        stmt = stmt.where(
            Classroom.name.ilike(f"%{search}%")
        )

    stmt = stmt.order_by(Classroom.id.desc())

    return db.paginate(
        stmt,
        page=page,
        per_page=per_page,
        error_out=False,
    )


# ============================ 3. Get Single Classroom ============================

def get_classroom(classroom_id, school_id):
    """
    Get a classroom belonging to the specified school.
    """

    return db.session.scalar(
        db.select(Classroom).where(
            Classroom.id == classroom_id,
            Classroom.school_id == school_id,
        )
    )


# ============================ 4. Get Classroom List ============================

def get_all_classroom_list(school_id):
    """
    Get all classrooms belonging to the specified school.
    """

    stmt = (
        db.select(Classroom)
        .where(Classroom.school_id == school_id)
        .order_by(Classroom.id.desc())
    )

    return db.session.scalars(stmt).all()


# ============================ 5. Update Classroom ============================

def update_classroom(
    classroom_id,
    data,
    school_id,
    actor_id=None,
):
    """
    Update a classroom belonging to the specified school.
    """

    classroom = get_classroom(
        classroom_id=classroom_id,
        school_id=school_id,
    )

    if classroom is None:
        return None

    changes = {}

    if data.name is not None and data.name != classroom.name:
        changes["name"] = {
            "before": classroom.name,
            "after": data.name,
        }

    if (
        data.capacity is not None
        and data.capacity != classroom.capacity
    ):
        changes["capacity"] = {
            "before": classroom.capacity,
            "after": data.capacity,
        }

    if (
        data.location is not None
        and data.location != classroom.location
    ):
        changes["location"] = {
            "before": classroom.location,
            "after": data.location,
        }

    if (
        data.teacher_id is not None
        and data.teacher_id != classroom.teacher_id
    ):
        changes["teacher_id"] = {
            "before": classroom.teacher_id,
            "after": data.teacher_id,
        }

    if data.name is not None:
        classroom.name = data.name

    if data.capacity is not None:
        classroom.capacity = data.capacity

    if data.location is not None:
        classroom.location = data.location

    if data.teacher_id is not None:
        classroom.teacher_id = data.teacher_id or None

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="Could not update classroom — check for duplicate name."
        )

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Classroom",
            resource_id=classroom.id,
            description=f"Updated classroom {classroom.name}",
            changes=changes,
            school_id=school_id,
        )

    db.session.commit()

    return classroom


# ============================ 6. Delete Classroom ============================

def delete_classroom(
    classroom_id,
    school_id,
    actor_id=None,
):
    """
    Delete a classroom belonging to the specified school.
    """

    classroom = get_classroom(
        classroom_id=classroom_id,
        school_id=school_id,
    )

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
            school_id=school_id,
        )

    db.session.commit()

    return True


# ============================ 7. Bulk Assign Students ============================

def bulk_assign_students(
    classroom_id,
    student_ids,
    school_id,
    actor_id=None,
):
    """
    Assign students to a classroom.

    Both the classroom and students must belong to the same school.
    """

    classroom = get_classroom(
        classroom_id=classroom_id,
        school_id=school_id,
    )

    if classroom is None:
        return None

    if not student_ids:
        return {
            "classroom_id": classroom.id,
            "assigned_ids": [],
            "missing_ids": [],
        }

    stmt = db.select(Student).where(
        Student.id.in_(student_ids),
        Student.school_id == school_id,
    )

    students = db.session.scalars(stmt).all()

    found_ids = {student.id for student in students}

    missing_ids = [
        student_id
        for student_id in student_ids
        if student_id not in found_ids
    ]

    for student in students:
        student.classroom_id = classroom.id

    db.session.flush()

    if actor_id and found_ids:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.BULK_ACTION,
            resource_type="Classroom",
            resource_id=classroom.id,
            description=(
                f"Bulk assigned {len(found_ids)} student(s) "
                f"to classroom {classroom.name}"
            ),
            changes={
                "assigned_student_ids": sorted(found_ids),
            },
            school_id=school_id,
        )

    db.session.commit()

    return {
        "classroom_id": classroom.id,
        "assigned_ids": sorted(found_ids),
        "missing_ids": missing_ids,
    }


# ============================ 8. Serialize Classroom ============================

def serialize_classroom(classroom):
    """
    Serialize a classroom for API responses.
    """

    return {
        "id": classroom.id,
        "school_id": classroom.school_id,
        "name": classroom.name,
        "capacity": classroom.capacity,
        "location": classroom.location,
        "teacher_id": classroom.teacher_id,
        "is_final_level": classroom.is_final_level,
        "level": classroom.level,
        "section_id": classroom.section_id,
    }
