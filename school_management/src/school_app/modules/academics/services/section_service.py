from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.section import Section
from school_app.models.academic_level import AcademicLevel
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ create section ============================

def create_section(data, actor_id):
    actor = db.session.get(User, actor_id)

    if actor is None:
        abort(401, description="Authenticated user not found.")

    level = db.session.get(AcademicLevel, data.level_id)

    if level is None:
        abort(
            404,
            description=f"Academic level with ID {data.level_id} not found.",
        )

    # Tenant isolation:
    # The academic level must belong to the same school as the actor.
    if level.school_id != actor.school_id:
        abort(404, description="Academic level not found.")

    section = Section(
        school_id=actor.school_id,
        level_id=data.level_id,
        name=data.name,
        display_order=data.display_order,
    )

    db.session.add(section)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description=(
                "Could not create section — check for duplicate "
                "name within this level."
            ),
        )

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="Section",
        resource_id=section.id,
        description=(
            f"Created section {section.name} "
            f"under level {level.name}"
        ),
    )

    db.session.commit()

    return section


# =============================== get all sections =============================

def get_all_sections(
    level_id=None,
    search="",
    include_inactive=False,
    page=1,
    per_page=10,
    school_id=None,
):
    stmt = db.select(Section)

    if school_id is not None:
        stmt = stmt.where(Section.school_id == school_id)

    if level_id is not None:
        stmt = stmt.where(Section.level_id == level_id)

    if search:
        stmt = stmt.where(Section.name.ilike(f"%{search}%"))

    if not include_inactive:
        stmt = stmt.where(Section.is_active.is_(True))

    stmt = stmt.order_by(
        Section.display_order.asc(),
        Section.id.asc(),
    )

    return db.paginate(
        stmt,
        page=page,
        per_page=per_page,
        error_out=False,
    )


# ============================== get section ===================================

def get_section(section_id, school_id=None):
    stmt = db.select(Section).where(
        Section.id == section_id
    )

    if school_id is not None:
        stmt = stmt.where(
            Section.school_id == school_id
        )

    return db.session.execute(stmt).scalar_one_or_none()


# ============================== update section =================================

def update_section(data, section_id, actor_id):
    actor = db.session.get(User, actor_id)

    if actor is None:
        abort(401, description="Authenticated user not found.")

    section = get_section(
        section_id,
        school_id=actor.school_id,
    )

    if section is None:
        return None

    changes = {}

    if data.name is not None and data.name != section.name:
        changes["name"] = {
            "before": section.name,
            "after": data.name,
        }
        section.name = data.name

    if (
        data.display_order is not None
        and data.display_order != section.display_order
    ):
        changes["display_order"] = {
            "before": section.display_order,
            "after": data.display_order,
        }
        section.display_order = data.display_order

    if (
        data.is_active is not None
        and data.is_active != section.is_active
    ):
        changes["is_active"] = {
            "before": section.is_active,
            "after": data.is_active,
        }
        section.is_active = data.is_active

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description=(
                "Could not update section — check for duplicate "
                "name within this level."
            ),
        )

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Section",
            resource_id=section.id,
            description=f"Updated section {section.name}",
            changes=changes,
        )

    db.session.commit()

    return section


# ============================== delete section =================================

def delete_section(section_id, actor_id):
    actor = db.session.get(User, actor_id)

    if actor is None:
        abort(401, description="Authenticated user not found.")

    section = get_section(
        section_id,
        school_id=actor.school_id,
    )

    if section is None:
        return False

    if section.classrooms:
        abort(
            400,
            description=(
                f"Cannot delete section '{section.name}' — it still has "
                f"{len(section.classrooms)} classroom(s) assigned to it. "
                "Reassign those first."
            ),
        )

    section_name = section.name

    db.session.delete(section)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="Section",
        resource_id=section_id,
        description=f"Deleted section {section_name}",
    )

    db.session.commit()

    return True