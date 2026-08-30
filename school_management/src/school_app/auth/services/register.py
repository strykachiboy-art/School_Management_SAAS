# App/auth/services/register.py
from school_app.extensions import db
from school_app.models.user import User
from school_app.utils.password import hash_password


def register_user(username: str, email: str, password: str) -> tuple[User | None, str | None]:
    
    if User.query.filter_by(username=username).first():
        return None, "Username already taken"

    if User.query.filter_by(email=email).first():
        return None, "Email already registered"

    user = User(
        username=username,
        email=email,
        password=hash_password(password),
        role="student",  # forced
    )

    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)

    return user, None