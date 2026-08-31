# school_app/modules/academic_session/services.py

from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.academic_session import AcademicSession
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def create_academic_session(data, actor_id):
    """
    Create an AcademicSession record.

    - Validates required fields.
    - Derives school_id from data.school_id or from the actor's User record.
    - Normalizes name.
    - Returns the created AcademicSession instance.
    """
    # Basic validation
    name = getattr(data, "name", None)
    start_date = getattr(data, "start_date", None)
    end_date = getattr(data, "end_date", None)

    if not name:
        abort(400, description="Missing required field: name")
    if not start_date or not end_date:
        abort(400, description="Missing required start_date or end_date")
    if end_date <= start_date:
        abort(400, description="end_date must be strictly after start_date")

    # Determine school_id: prefer explicit value on request, else derive from actor
    school_id = getattr(data, "school_id", None)
    if school_id is None:
        actor = db.session.get(User, actor_id)
        if actor is None or getattr(actor, "school_id", None) is None:
            abort(400, description="Missing required field: school_id")
        school_id = actor.school_id

    # Normalize name
    normalized_name = name.strip()

    create_academic = AcademicSession(
        name=normalized_name,
        start_date=start_date,
        end_date=end_date,
        school_id=school_id,
    )

    db.session.add(create_academic)

    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        # Inspect underlying DB error message for a more accurate response
        orig_msg = ""
        try:
            orig_msg = str(exc.orig).lower()
        except Exception:
            orig_msg = str(exc).lower()

        if "uq_academic_session_name_per_school" in orig_msg or "unique" in orig_msg:
            abort(400, description="Could not create academic session — duplicate name for this school.")
        if "not null" in orig_msg or "null value" in orig_msg:
            abort(400, description="Could not create academic session — missing required field.")
        abort(400, description="Could not create academic session.")

    # Audit log and commit
    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="AcademicSession",
        resource_id=create_academic.id,
        description=f"Created academic session {create_academic.name}",
    )

    db.session.commit()
    return create_academic


def get_all_academic_session(search="", page=1, per_page=10):
    stmt = db.select(AcademicSession)
    if search:
        stmt = stmt.where(AcademicSession.name.ilike(f"%{search}%"))

    stmt = stmt.order_by(AcademicSession.id.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_academic_session(academic_id):
    return db.session.get(AcademicSession, academic_id)


def update_academic_session(data, academic_id, actor_id):
    academic_session = db.session.get(AcademicSession, academic_id)
    if academic_session is None:
        return None

    changes = {}
    if data.name and data.name != academic_session.name:
        changes["name"] = {"before": academic_session.name, "after": data.name}
    if data.start_date and data.start_date != academic_session.start_date:
        changes["start_date"] = {"before": str(academic_session.start_date), "after": str(data.start_date)}
    if data.end_date and data.end_date != academic_session.end_date:
        changes["end_date"] = {"before": str(academic_session.end_date), "after": str(data.end_date)}

    if data.name:
        academic_session.name = data.name.strip()
    if data.start_date:
        academic_session.start_date = data.start_date
    if data.end_date:
        academic_session.end_date = data.end_date

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update academic session — check for duplicate name.")

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="AcademicSession",
            resource_id=academic_session.id,
            description=f"Updated academic session {academic_session.name}",
            changes=changes,
        )

    db.session.commit()
    return academic_session


def delete_session(academic_id, actor_id):
    academic_session = db.session.get(AcademicSession, academic_id)
    if academic_session is None:
        return False

    session_name = academic_session.name
    db.session.delete(academic_session)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="AcademicSession",
        resource_id=academic_id,
        description=f"Deleted academic session {session_name}",
    )

    db.session.commit()
    return True


def activate_academic_session(academic_id, actor_id):
    academic_session = db.session.get(AcademicSession, academic_id)
    if academic_session is None:
        return None

    db.session.query(AcademicSession).filter(
        AcademicSession.id != academic_id
    ).update({AcademicSession.is_active: False}, synchronize_session=False)

    academic_session.is_active = True

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.UPDATE,
        resource_type="AcademicSession",
        resource_id=academic_session.id,
        description=f"Activated academic session {academic_session.name}",
    )

    db.session.commit()
    return academic_session
