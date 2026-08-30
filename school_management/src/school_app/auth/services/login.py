# App/auth/services/login.py
import secrets

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token

from school_app.extensions import db, redis_client
from school_app.models.user import User
from school_app.utils.password import verify_password


def authenticate_user(email: str, password: str) -> tuple[User | None, str | None]:
    """Verify credentials. Returns (user, None) on success, (None, error) on failure."""
    user = User.query.filter_by(email=email).first()

    if user is None or not verify_password(password, user.password):
        return None, "Invalid email or password"

    return user, None


def issue_tokens(user: User) -> dict:
    """Create a fresh access + refresh token pair, and record the refresh token as the
    only valid one for this user (whitelist, for rotation)."""
    access_token = create_access_token(
        identity=str(user.id), additional_claims={"role": user.role}
    )
    refresh_token = create_refresh_token(
        identity=str(user.id), additional_claims={"role": user.role}
    )

    decoded = decode_token(refresh_token)
    jti = decoded["jti"]
    exp = decoded["exp"]

    import time
    ttl = exp - int(time.time())
    if ttl > 0:
        redis_client.set(f"refresh_whitelist:{user.id}", jti, ex=ttl)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }