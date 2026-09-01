from flask import abort
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from school_app.utils.password import hash_password
from school_app.extensions import db
from school_app.models.teacher import Teacher
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def _get_teacher_or_404(teacher_id: int, school_id: int) -> Teacher:
    """Return a teacher belonging to the given school or raise 404."""
    teacher = db.session.scalar(
        db.select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == school_id,
        )
    )

    if teacher is None:
        abort(
            404,
            description=f"Teacher with ID {teacher_id} not found.",
        )

    return teacher


# ======================================================================
# Create
# ======================================================================

def create_teachers(form, school_id: int, actor_id=None):
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
            school_id=school_id,
            user_id=user.id,
            full_name=form.full_name,
            email=form.email,
            phone=form.phone,
            gender=form.gender,
            date_of_birth=form.date_of_birth,
        )

        db.session.add(teacher)
        db.session.flush()

    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="A user with that username or email already exists.",
        )

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Teacher",
            resource_id=teacher.id,
            description=(
                f"Created teacher profile for "
                f"{teacher.full_name} ({teacher.email})"
            ),
        )

    db.session.commit()

    return teacher


# ======================================================================
# Get all
# ======================================================================

def get_all_teachers(school_id: int):
    return db.session.scalars(
        db.select(Teacher)
        .where(Teacher.school_id == school_id)
        .order_by(Teacher.id.desc())
    ).all()


# ======================================================================
# Get by ID
# ======================================================================

def get_teacher_by_id(teacher_id: int, school_id: int):
    return _get_teacher_or_404(
        teacher_id,
        school_id,
    )


# ======================================================================
# Update
# ======================================================================

def update_teachers(
    teacher_id,
    form,
    school_id: int,
    actor_id=None,
):
    teacher = _get_teacher_or_404(
        teacher_id,
        school_id,
    )

    changes = {}

    # --------------------------------------------------------------
    # Full name
    # --------------------------------------------------------------

    if (
        form.full_name is not None
        and form.full_name != teacher.full_name
    ):
        changes["full_name"] = {
            "before": teacher.full_name,
            "after": form.full_name,
        }

        teacher.full_name = form.full_name

    # --------------------------------------------------------------
    # Email
    # --------------------------------------------------------------

    if (
        form.email is not None
        and form.email != teacher.email
    ):
        changes["email"] = {
            "before": teacher.email,
            "after": form.email,
        }

        teacher.email = form.email

        if teacher.user is not None:
            if teacher.user.email != form.email:
                changes["user_email"] = {
                    "before": teacher.user.email,
                    "after": form.email,
                }

            teacher.user.email = form.email

    # --------------------------------------------------------------
    # Phone
    # --------------------------------------------------------------

    if (
        form.phone is not None
        and form.phone != teacher.phone
    ):
        changes["phone"] = {
            "before": teacher.phone,
            "after": form.phone,
        }

        teacher.phone = form.phone

    # --------------------------------------------------------------
    # Gender
    # --------------------------------------------------------------

    if (
        form.gender is not None
        and form.gender != teacher.gender
    ):
        changes["gender"] = {
            "before": teacher.gender,
            "after": form.gender,
        }

        teacher.gender = form.gender

    # --------------------------------------------------------------
    # Date of birth
    # --------------------------------------------------------------

    if (
        form.date_of_birth is not None
        and form.date_of_birth != teacher.date_of_birth
    ):
        changes["date_of_birth"] = {
            "before": (
                teacher.date_of_birth.isoformat()
                if teacher.date_of_birth
                else None
            ),
            "after": form.date_of_birth.isoformat(),
        }

        teacher.date_of_birth = form.date_of_birth

    try:
        db.session.flush()

    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="That email is already in use.",
        )

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Teacher",
            resource_id=teacher.id,
            description=(
                f"Updated teacher ID {teacher.id} "
                f"({teacher.full_name})"
            ),
            changes=changes,
        )

    db.session.commit()

    return teacher


# ======================================================================
# Delete
# ======================================================================

def delete_teacher(
    teacher_id,
    school_id: int,
    actor_id=None,
):
    teacher = _get_teacher_or_404(
        teacher_id,
        school_id,
    )

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
            description=(
                f"Deleted teacher ID {teacher_id} "
                f"({teacher_name})"
            ),
        )

    db.session.commit()

    return True


# ======================================================================
# Filter
# ======================================================================

def filter_Teacher(
    school_id: int,
    **filters,
):
    query = db.select(Teacher).where(
        Teacher.school_id == school_id
    )

    if "id" in filters:
        query = query.where(
            Teacher.id == filters["id"]
        )

    if "user_id" in filters:
        query = query.where(
            Teacher.user_id == filters["user_id"]
        )

    query = query.order_by(
        Teacher.id.desc()
    )

    return db.session.scalars(query).all()


# ======================================================================
# Search
# ======================================================================

def search_teacher_info(
    search,
    school_id: int,
):
    return db.session.scalars(
        db.select(Teacher)
        .join(Teacher.user)
        .where(
            Teacher.school_id == school_id,
            or_(
                Teacher.full_name.ilike(
                    f"%{search}%"
                ),
                User.username.ilike(
                    f"%{search}%"
                ),
            ),
        )
        .order_by(Teacher.id.desc())
    ).all()


# ======================================================================
# Pagination
# ======================================================================

def paginate_teachers(
    school_id: int,
    page=1,
    per_page=10,
):
    return (
        Teacher.query
        .filter(
            Teacher.school_id == school_id
        )
        .order_by(
            Teacher.id.desc()
        )
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
    )


# ======================================================================
# Sort
# ======================================================================

def sort_teacher(
    school_id: int,
    page=1,
    per_page=10,
):
    return (
        Teacher.query
        .filter(
            Teacher.school_id == school_id
        )
        .order_by(
            Teacher.id.desc()
        )
        .paginate(
            page=page,
            per_page=per_page,
            error_out=False,
        )
    )