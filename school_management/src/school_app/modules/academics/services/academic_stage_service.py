# src/school_app/modules/academics/services/academic_stage_service.py

from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.academic_stage import AcademicStage
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def create_academic_stage(data, actor_id):
    # Validate required fields
    name = getattr(data, "name", None)
    if not name:
        abort(400, description="Missing required field: name")

    # Determine school_id: prefer explicit value on request, else derive from actor
    school_id = getattr(data, "school_id", None)
    if school_id is None:
        actor = db.session.get(User, actor_id)
        if actor is None or getattr(actor, "school_id", None) is None:
            abort(400, description="Missing required field: school_id")
        school_id = actor.school_id

    # Normalize fields
    normalized_name = name.strip()
    code = getattr(data, "code", None)
    num_code = getattr(data, "num_code", None)
    if code is None and num_code is not None:
        code = str(num_code)
    if isinstance(code, str):
        code = code.strip()

    display_order = getattr(data, "display_order", None)
    is_active = bool(getattr(data, "is_active", False))

    # Instantiated without 'code' and 'num_code' since the model doesn't have those columns
    stage = AcademicStage(
        name=normalized_name,
        display_order=display_order,
        is_active=is_active,
        school_id=school_id,
    )

    db.session.add(stage)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        orig_msg = ""
        try:
            orig_msg = str(exc.orig).lower()
        except Exception:
            orig_msg = str(exc).lower()

        if "unique" in orig_msg or "uq_" in orig_msg:
            abort(400, description="Could not create academic stage — duplicate for this school.")
        if "not null" in orig_msg or "null value" in orig_msg:
            abort(400, description="Could not create academic stage — missing required field.")
        abort(400, description="Could not create academic stage.")

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="AcademicStage",
        resource_id=stage.id,
        description=f"Created academic stage {stage.name}",
    )

    db.session.commit()
    return stage


def get_all_academic_stages(search="", include_inactive=False, page=1, per_page=10):
    stmt = db.select(AcademicStage)
    if search:
        stmt = stmt.where(AcademicStage.name.ilike(f"%{search}%"))
    if not include_inactive:
        stmt = stmt.where(AcademicStage.is_active.is_(True))

    stmt = stmt.order_by(AcademicStage.display_order.asc(), AcademicStage.id.asc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_academic_stage(stage_id):
    return db.session.get(AcademicStage, stage_id)


def update_academic_stage(data, stage_id, actor_id):
    stage = db.session.get(AcademicStage, stage_id)
    if stage is None:
        return None

    changes = {}

    if getattr(data, "name", None) is not None:
        new_name = data.name.strip() if isinstance(data.name, str) else data.name
        if new_name != stage.name:
            changes["name"] = {"before": stage.name, "after": new_name}
            stage.name = new_name

    # Handle display order updates safely
    if getattr(data, "display_order", None) is not None:
        if data.display_order != stage.display_order:
            changes["display_order"] = {"before": stage.display_order, "after": data.display_order}
            stage.display_order = data.display_order

    if getattr(data, "is_active", None) is not None:
        if data.is_active != stage.is_active:
            changes["is_active"] = {"before": stage.is_active, "after": data.is_active}
            stage.is_active = data.is_active

    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        orig_msg = ""
        try:
            orig_msg = str(exc.orig).lower()
        except Exception:
            orig_msg = str(exc).lower()

        if "unique" in orig_msg or "uq_" in orig_msg:
            abort(400, description="Could not update academic stage — duplicate for this school.")
        if "not null" in orig_msg or "null value" in orig_msg:
            abort(400, description="Could not update academic stage — missing required field.")
        abort(400, description="Could not update academic stage.")

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


def delete_academic_stage(stage_id, actor_id):
    stage = db.session.get(AcademicStage, stage_id)
    if stage is None:
        return False

    if getattr(stage, "levels", None):
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