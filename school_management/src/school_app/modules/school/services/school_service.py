from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.school import School
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ create school ============================

def create_school(data, actor_id):
    school = School(
        name=data.name,
        slug=data.slug,
        country=data.country,
        timezone=data.timezone,
        currency=data.currency,
        locale=data.locale,
    )

    db.session.add(school)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create school — slug is already in use.")

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="School",
        resource_id=school.id,
        description=f"Created school {school.name}",
    )

    db.session.commit()
    return school


# =============================== get all schools =============================

def get_all_schools(search="", include_inactive=False, page=1, per_page=10):
    stmt = db.select(School)
    if search:
        stmt = stmt.where(School.name.ilike(f"%{search}%"))
    if not include_inactive:
        stmt = stmt.where(School.is_active.is_(True))

    stmt = stmt.order_by(School.name.asc())

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


# ============================== get school ===================================

def get_school(school_id):
    return db.session.get(School, school_id)


def get_school_by_slug(slug):
    stmt = db.select(School).where(School.slug == slug.lower())
    return db.session.scalars(stmt).first()


# ============================== update school =================================

def update_school(data, school_id, actor_id):
    school = db.session.get(School, school_id)
    if school is None:
        return None

    changes = {}
    for field in ("name", "country", "timezone", "currency", "locale", "is_active", "onboarding_completed"):
        new_value = getattr(data, field)
        if new_value is not None and new_value != getattr(school, field):
            changes[field] = {"before": getattr(school, field), "after": new_value}
            setattr(school, field, new_value)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update school.")

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="School",
            resource_id=school.id,
            description=f"Updated school {school.name}",
            changes=changes,
        )

    db.session.commit()
    return school


# ============================== delete school =================================

def delete_school(school_id, actor_id):
    """Blocks deletion if the school still has any users attached — a
    School with real data (students, staff, everything hanging off those
    User rows) should be deactivated (is_active=False via update_school),
    not deleted. Deleting a School with active users would either orphan
    every one of them (school_id is nullable, so this wouldn't even fail
    at the DB level) or, worse, silently misattribute them once the FK
    eventually becomes required — neither is safe, so it's blocked outright
    here rather than relying on the FK alone.
    """
    school = db.session.get(School, school_id)
    if school is None:
        return False

    user_count = db.session.scalar(
        db.select(db.func.count()).select_from(User).where(User.school_id == school_id)
    )
    if user_count and user_count > 0:
        abort(
            400,
            description=(
                f"Cannot delete school '{school.name}' — it still has {user_count} user(s) "
                "attached. Deactivate it instead (is_active=false), or reassign/remove users first."
            ),
        )

    school_name = school.name
    db.session.delete(school)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="School",
        resource_id=school_id,
        description=f"Deleted school {school_name}",
    )

    db.session.commit()
    return True