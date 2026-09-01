from flask import abort
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.subject import Subject
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ Create Subject ============================

def create_subject(form, actor_id=None):

    school_id = None

    if actor_id is not None:
        actor = db.session.get(User, actor_id)

        if actor is None:
            abort(404, description="Actor not found.")

        school_id = actor.school_id

    if school_id is None:
        abort(400, description="Unable to determine the actor's school.")

    subject = Subject(
        school_id=school_id,
        name=form.name,
        code=form.code,
        description=form.description,
    )

    db.session.add(subject)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="A subject with that name or code already exists in this school.",
        )

    if actor_id is not None:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=f"Created subject {subject.name} ({subject.code})",
        )

    db.session.commit()

    return subject


# ============================ Get Subject ============================

def get_subject(subject_id):
    return db.session.get(Subject, subject_id)


# ============================ Get All Subjects ============================

def get_all_subjects(school_id=None):
    """
    Return subjects belonging to a specific school.

    Passing school_id is recommended so subjects from another tenant
    cannot be exposed.
    """

    query = Subject.query

    if school_id is not None:
        query = query.filter(Subject.school_id == school_id)

    return query.order_by(Subject.id.desc()).all()


# ============================ Update Subject ============================

def update_subject(subject_id, form, actor_id=None):
    subject = get_subject(subject_id)

    if subject is None:
        return None

    # Tenant protection
    if actor_id is not None:
        actor = db.session.get(User, actor_id)

        if actor is None:
            abort(404, description="Actor not found.")

        if subject.school_id != actor.school_id:
            abort(404, description="Subject not found.")

    changes = {}

    if form.name is not None and form.name != subject.name:
        changes["name"] = {
            "before": subject.name,
            "after": form.name,
        }
        subject.name = form.name

    if form.code is not None and form.code != subject.code:
        changes["code"] = {
            "before": subject.code,
            "after": form.code,
        }
        subject.code = form.code

    if form.description is not None and form.description != subject.description:
        changes["description"] = {
            "before": subject.description,
            "after": form.description,
        }
        subject.description = form.description

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="A subject with that name or code already exists in this school.",
        )

    if changes and actor_id is not None:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=f"Updated subject ID {subject.id} ({subject.code})",
            changes=changes,
        )

    db.session.commit()

    return subject


# ============================ Delete Subject ============================

def delete_subject(subject_id, actor_id=None):
    subject = db.session.get(Subject, subject_id)

    if subject is None:
        return False

    # Tenant protection
    if actor_id is not None:
        actor = db.session.get(User, actor_id)

        if actor is None:
            abort(404, description="Actor not found.")

        if subject.school_id != actor.school_id:
            abort(404, description="Subject not found.")

    subject_code = subject.code

    db.session.delete(subject)

    if actor_id is not None:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Subject",
            resource_id=subject_id,
            description=f"Deleted subject ID {subject_id} ({subject_code})",
        )

    db.session.commit()

    return True


# ============================ Search Subject ============================

def search_subject_info(search, school_id=None):
    query = Subject.query.filter(
        or_(
            Subject.name.ilike(f"%{search}%"),
            Subject.code.ilike(f"%{search}%"),
        )
    )

    if school_id is not None:
        query = query.filter(Subject.school_id == school_id)

    return query.order_by(Subject.id.desc()).all()


# ============================ Serialize Subject ============================

def serialize_subject(subject):
    return {
        "id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "description": subject.description,
        "created_at": (
            subject.created_at.isoformat()
            if subject.created_at
            else None
        ),
        "updated_at": (
            subject.updated_at.isoformat()
            if subject.updated_at
            else None
        ),
    }


# ============================ Paginate Subject ============================

def paginate_subject(
    page=1,
    per_page=10,
    school_id=None,
):
    query = Subject.query

    if school_id is not None:
        query = query.filter(Subject.school_id == school_id)

    return query.order_by(
        Subject.id.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
