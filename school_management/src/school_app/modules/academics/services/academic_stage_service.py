from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.academic_stage import AcademicStage
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ create academic stage ============================

def create_academic_stage(data, actor_id):
    stage = AcademicStage(
        name=data.name,
        display_order=data.display_order,
    )

    db.session.add(stage)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create academic stage — check for duplicate name.")

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="AcademicStage",
        resource_id=stage.id,
        description=f"Created academic stage {stage.name}",
    )

    db.session.commit()

    return stage


# =============================== get all academic stages =============================

def get_all_academic_stages(search="", include_inactive=False, page=1, per_page=10):
    stmt = db.select(AcademicStage)
    if search:
        stmt = stmt.where(AcademicStage.name.ilike(f"%{search}%"))
    if not include_inactive:
        stmt = stmt.where(AcademicStage.is_active.is_(True))

    stmt = stmt.order_by(AcademicStage.display_order.asc(), AcademicStage.id.asc())

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


# ============================== get academic stage ===================================

def get_academic_stage(stage_id):
    return db.session.get(AcademicStage, stage_id)


# ============================== update academic stage =================================

def update_academic_stage(data, stage_id, actor_id):
    stage = db.session.get(AcademicStage, stage_id)

    if stage is None:
        return None

    changes = {}
    if data.name is not None and data.name != stage.name:
        changes["name"] = {"before": stage.name, "after": data.name}
        stage.name = data.name
    if data.display_order is not None and data.display_order != stage.display_order:
        changes["display_order"] = {"before": stage.display_order, "after": data.display_order}
        stage.display_order = data.display_order
    if data.is_active is not None and data.is_active != stage.is_active:
        changes["is_active"] = {"before": stage.is_active, "after": data.is_active}
        stage.is_active = data.is_active

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update academic stage — check for duplicate name.")

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="AcademicStage",
            resource_id=stage.id,
            description=f"Updated academic stage {stage.name}",
            changes=changes,
        )

    db.session.commit()

    return stage


# ============================== delete academic stage =================================

def delete_academic_stage(stage_id, actor_id):
    stage = db.session.get(AcademicStage, stage_id)

    if stage is None:
        return False

    if stage.levels:
        abort(
            400,
            description=(
                f"Cannot delete academic stage '{stage.name}' — it still has "
                f"{len(stage.levels)} level(s) under it. Reassign or delete those first."
            ),
        )

    stage_name = stage.name
    db.session.delete(stage)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="AcademicStage",
        resource_id=stage_id,
        description=f"Deleted academic stage {stage_name}",
    )

    db.session.commit()

    return True