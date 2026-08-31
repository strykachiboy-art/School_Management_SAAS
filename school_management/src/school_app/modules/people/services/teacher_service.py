from flask import abort
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from school_app.utils.password import hash_password

from school_app.extensions import db
from school_app.models.teacher import Teacher
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def create_teachers(form, actor_id=None):
    user = User(
        username=form.username,
        email=form.email,
        password=hash_password(form.password),
        role="teacher",
    )
    db.session.add(user)

    try:
        db.session.flush()

        teacher = Teacher(
            user_id=user.id, 
            full_name=form.full_name,
            email=form.email,
            phone=form.phone,
        )
        db.session.add(teacher)
        db.session.flush()

    except IntegrityError:
        db.session.rollback()
        abort(400, description="A user with that username or email already exists.")

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Teacher",
            resource_id=teacher.id,
            description=f"Created teacher profile for {teacher.full_name} ({teacher.email})",
        )
        
    db.session.commit()

    return teacher


def get_all_teachers():
    return Teacher.query.order_by(Teacher.id.desc()).all()


def get_teacher_by_id(teacher_id):
    return db.session.get(Teacher, teacher_id)


def update_teachers(teacher_id, form, actor_id=None):
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        return None

    changes = {}
    if form.full_name and form.full_name != teacher.full_name:
        changes["full_name"] = {"before": teacher.full_name, "after": form.full_name}
    if form.email and form.email != teacher.email:
        changes["email"] = {"before": teacher.email, "after": form.email}
    if form.phone and form.phone != teacher.phone:
        changes["phone"] = {"before": teacher.phone, "after": form.phone}

    teacher.full_name = form.full_name or teacher.full_name
    teacher.email = form.email or teacher.email
    teacher.phone = form.phone or teacher.phone

    if teacher.user is not None and form.email:
        if teacher.user.email != form.email:
            changes["user_email"] = {"before": teacher.user.email, "after": form.email}
        teacher.user.email = form.email

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="That email is already in use.")

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Teacher",
            resource_id=teacher.id,
            description=f"Updated teacher ID {teacher.id} ({teacher.full_name})",
            changes=changes,
        )
        
    db.session.commit()

    return teacher


def delete_teacher(teacher_id, actor_id=None):
    teacher = db.session.get(Teacher, teacher_id)
    if teacher is None:
        return False

    teacher_name = teacher.full_name
    user = teacher.user
    db.session.delete(teacher)
    if user is not None:
        db.session.delete(user)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Teacher",
            resource_id=teacher_id,
            description=f"Deleted teacher ID {teacher_id} ({teacher_name})",
        )
        
    db.session.commit()

    return True


def filter_Teacher(**filters):
    query = Teacher.query
    if "id" in filters:
        query = query.filter(Teacher.id == filters["id"])
    if "user_id" in filters:
        query = query.filter(Teacher.user_id == filters["user_id"])
    return query.order_by(Teacher.id.desc()).all()


def search_teacher_info(search):
    return (
        Teacher.query.join(Teacher.user)
        .filter(or_(Teacher.full_name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))
        .order_by(Teacher.id.desc())
        .all()
    )


def paginate_teachers(page=1, per_page=10):
    return Teacher.query.order_by(Teacher.id.desc()).paginate(page=page, per_page=per_page, error_out=False)


def sort_teacher(page=1, per_page=10):
    return Teacher.query.order_by(Teacher.id.desc()).paginate(page=page, per_page=per_page, error_out=False)