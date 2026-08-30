from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.teacher import Teacher
from school_app.models.teacher_permission import TeacherPermission
from school_app.enums.permission import Permission
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def _get_teacher_or_404(teacher_id: int) -> Teacher:
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        abort(404, description=f"Teacher with ID {teacher_id} not found.")
    return teacher


def assign_teacher_permission(teacher_id: int, permission: Permission, actor_id=None) -> TeacherPermission:
    """Admin assigns a single permission to a teacher. Prevents duplicates."""
    teacher = _get_teacher_or_404(teacher_id)  # Ensure this returns the Teacher model instance

    existing = db.session.scalar(
        db.select(TeacherPermission).where(
            TeacherPermission.teacher_id == teacher_id,
            TeacherPermission.permission == permission,
        )
    )
    if existing:
        abort(400, description=f"Teacher already has the '{permission.value}' permission.")

    # Pass school_id from the teacher record
    record = TeacherPermission(
        school_id=teacher.school_id,
        teacher_id=teacher_id,
        permission=permission
    )
    db.session.add(record)

    try:
        db.session.flush()
    except Exception as e:
        db.session.rollback()
        raise e

    return record


def get_teacher_permissions(teacher_id: int) -> list[TeacherPermission]:
    """All permissions currently assigned to one teacher."""
    _get_teacher_or_404(teacher_id)

    return db.session.scalars(
        db.select(TeacherPermission).where(TeacherPermission.teacher_id == teacher_id)
    ).all()


def get_all_teacher_permissions() -> list[TeacherPermission]:
    """Admin view — every permission assignment, across all teachers."""
    return db.session.scalars(db.select(TeacherPermission)).all()


def update_teacher_permissions(teacher_id: int, permissions: list[Permission], actor_id=None) -> list[TeacherPermission]:
    """
    Replaces a teacher's full permission set with the given list.
    Only adds what's missing and removes what's no longer wanted —
    unchanged permissions keep their original row untouched.
    """
    _get_teacher_or_404(teacher_id)

    desired = set(permissions)

    existing_records = db.session.scalars(
        db.select(TeacherPermission).where(TeacherPermission.teacher_id == teacher_id)
    ).all()
    existing_permissions = {r.permission for r in existing_records}

    added = desired - existing_permissions
    removed = existing_permissions - desired

    # Remove permissions no longer wanted.
    for record in existing_records:
        if record.permission not in desired:
            db.session.delete(record)

    # Add permissions that are newly wanted.
    new_records = [TeacherPermission(teacher_id=teacher_id, permission=p) for p in added]
    db.session.add_all(new_records)
    db.session.flush()

    if (added or removed) and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Teacher",
            resource_id=teacher_id,
            description=f"Updated permissions for teacher ID {teacher_id}",
            changes={
                "added": [p.value for p in added],
                "removed": [p.value for p in removed],
            },
        )
        
    db.session.commit()

    return db.session.scalars(
        db.select(TeacherPermission).where(TeacherPermission.teacher_id == teacher_id)
    ).all()


def remove_teacher_permission(teacher_id: int, permission: Permission, actor_id=None) -> bool:
    """Admin revokes a specific permission from a teacher."""
    record = db.session.scalar(
        db.select(TeacherPermission).where(
            TeacherPermission.teacher_id == teacher_id,
            TeacherPermission.permission == permission,
        )
    )
    if record is None:
        abort(404, description=f"Teacher does not have the '{permission.value}' permission.")

    record_id = record.id
    db.session.delete(record)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="TeacherPermission",
            resource_id=record_id,
            description=f"Revoked permission '{permission.value}' from teacher ID {teacher_id}",
        )
        
    db.session.commit()
        
    return True