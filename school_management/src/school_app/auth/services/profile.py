from sqlalchemy.exc import SQLAlchemyError
from school_app.models.user import User
from school_app.extensions import db
from school_app.auth.request.profile import ProfileUpdateRequest

from sqlalchemy.exc import SQLAlchemyError
from school_app.models.user import User
from school_app.extensions import db
from school_app.auth.request.profile import ProfileUpdateRequest


def update_profile(user: User, data: ProfileUpdateRequest) -> User:
    try:
        # Check username uniqueness
        if data.username is not None and data.username != user.username:
            existing_user = User.query.filter(
                User.username == data.username,
                User.id != user.id
            ).first()
            if existing_user:
                db.session.rollback()
                raise ValueError("Username already exists")
            user.username = data.username

        # Check email uniqueness
        if data.email is not None and data.email != user.email:
            existing_user = User.query.filter(
                User.email == data.email,
                User.id != user.id
            ).first()
            if existing_user:
                db.session.rollback()
                raise ValueError("Email already exists")
            user.email = data.email

        db.session.commit()
        return user
    except SQLAlchemyError as e:
        db.session.rollback()
        raise RuntimeError("A database error occurred while updating the profile.") from e