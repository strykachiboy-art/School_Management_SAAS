from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.academic_level import AcademicLevel
from school_app.models.academic_stage import AcademicStage
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ create academic level ============================

def create_academic_level(data, actor_id):
    stage = db.session.get(AcademicStage, data.stage_id)
    if stage is None:
        abort(404, description=f"Academic stage with ID {data.stage_id} not found.")

    level = AcademicLevel(
        school_id=stage.school_id,
        stage_id=data.stage_id,
        name=data.name,
        display_order=data.display_order,
    )

    db.session.add(level)

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        error_msg = str(e).lower()
        if "uq_level_name_per_stage_per_school" in error_msg or "unique constraint" in error_msg:
            abort(400, description="Could not create academic level — check for duplicate name within this stage.")
        raise e

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="AcademicLevel",
        resource_id=level.id,
        description=f"Created academic level {level.name} under stage {stage.name}",
    )

    db.session.commit()

    return level


# =============================== get all academic levels =============================

def get_all_academic_levels(school_id, stage_id=None, search="", include_inactive=False, page=1, per_page=10):
    stmt = db.select(AcademicLevel).where(AcademicLevel.school_id == school_id)
    if stage_id is not None:
        stmt = stmt.where(AcademicLevel.stage_id == stage_id)
    if search:
        stmt = stmt.where(AcademicLevel.name.ilike(f"%{search}%"))
    if not include_inactive:
        stmt = stmt.where(AcademicLevel.is_active.is_(True))

    stmt = stmt.order_by(AcademicLevel.display_order.asc(), AcademicLevel.id.asc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


# ============================== get academic level ===================================

def get_academic_level(level_id):
    return db.session.get(AcademicLevel, level_id)


# ============================== update academic level =================================

def update_academic_level(data, level_id, actor_id):
    level = db.session.get(AcademicLevel, level_id)

    if level is None:
        return None

    changes = {}
    if data.name is not None and data.name != level.name:
        changes["name"] = {"before": level.name, "after": data.name}
        level.name = data.name
    if data.display_order is not None and data.display_order != level.display_order:
        changes["display_order"] = {"before": level.display_order, "after": data.display_order}
        level.display_order = data.display_order
    if data.is_active is not None and data.is_active != level.is_active:
        changes["is_active"] = {"before": level.is_active, "after": data.is_active}
        level.is_active = data.is_active

    try:
        db.session.flush()
    except IntegrityError as e:
        db.session.rollback()
        error_msg = str(e).lower()
        if "uq_level_name_per_stage_per_school" in error_msg or "unique constraint" in error_msg:
            abort(400, description="Could not update academic level — check for duplicate name within this stage.")
        raise e

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="AcademicLevel",
            resource_id=level.id,
            description=f"Updated academic level {level.name}",
            changes=changes,
        )

    db.session.commit()

    return level


# ============================== delete academic level =================================

def delete_academic_level(level_id, actor_id):
    level = db.session.get(AcademicLevel, level_id)

    if level is None:
        return False

    if level.sections:
        abort(
            400,
            description=(
                f"Cannot delete academic level '{level.name}' — it still has "
                f"{len(level.sections)} section(s) under it. Reassign or delete those first."
            ),
        )

    level_name = level.name
    db.session.delete(level)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="AcademicLevel",
        resource_id=level_id,
        description=f"Deleted academic level {level_name}",
    )

    db.session.commit()

    return True