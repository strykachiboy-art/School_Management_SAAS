from flask import abort
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.subject import Subject
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def create_subject(form, actor_id=None):
    subject = Subject(
        name=form.name,
        code=form.code,
        description=form.description,
    )
    db.session.add(subject)

    try:
        db.session.flush()  # Forces SQL execution to catch unique code violations and populate subject.id
    except IntegrityError:
        db.session.rollback()
        abort(400, description="A subject with that code already exists.")

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Subject",
            resource_id=subject.id,
            description=f"Created subject {subject.name} ({subject.code})",
        )
        
    db.session.commit()

    return subject


def get_subject(subject_id):
    return db.session.get(Subject, subject_id)


def get_all_subjects():
    return Subject.query.order_by(Subject.id.desc()).all()


def update_subject(subject_id, form, actor_id=None):
    subject = get_subject(subject_id)
    if subject is None:
        return None

    changes = {}
    if form.name is not None and form.name != subject.name:
        changes["name"] = {"before": subject.name, "after": form.name}
    if form.code is not None and form.code != subject.code:
        changes["code"] = {"before": subject.code, "after": form.code}
    if form.description is not None and form.description != subject.description:
        changes["description"] = {"before": subject.description, "after": form.description}

    if form.name is not None:
        subject.name = form.name
    if form.code is not None:
        subject.code = form.code
    if form.description is not None:
        subject.description = form.description

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="A subject with that code already exists.")

    if changes and actor_id:
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


def delete_subject(subject_id, actor_id=None):
    subject = db.session.get(Subject, subject_id)
    if subject is None:
        return False

    subject_code = subject.code
    db.session.delete(subject)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Subject",
            resource_id=subject_id,
            description=f"Deleted subject ID {subject_id} ({subject_code})",
        )
        
    db.session.commit()

    return True


def search_subject_info(search):
    return (
        Subject.query.filter(or_(Subject.name.ilike(f"%{search}%"), Subject.code.ilike(f"%{search}%")))
        .order_by(Subject.id.desc())
        .all()
    )


def serialize_subject(subject):
    return {
        "id": subject.id,
        "name": subject.name,
        "code": subject.code,
        "description": subject.description,
        "created_at": subject.created_at.isoformat() if subject.created_at else None,
        "updated_at": subject.updated_at.isoformat() if subject.updated_at else None,
    }


def paginate_subject(page=1, per_page=10):
    return Subject.query.order_by(Subject.id.desc()).paginate(page=page, per_page=per_page, error_out=False)