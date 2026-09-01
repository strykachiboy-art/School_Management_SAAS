# App/auth/services/login.py
import secrets

from flask_jwt_extended import create_access_token, create_refresh_token, decode_token
import redis

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
    claims = {"role": user.role}
    if getattr(user, "school_id", None) is not None:
        claims["school_id"] = user.school_id

    access_token = create_access_token(
        identity=str(user.id), additional_claims=claims
    )
    refresh_token = create_refresh_token(
        identity=str(user.id), additional_claims=claims
    )

    decoded = decode_token(refresh_token)
    jti = decoded["jti"]
    exp = decoded["exp"]

    import time
    ttl = exp - int(time.time())
    if ttl > 0:
        try:
            redis_client.set(f"refresh_whitelist:{user.id}", jti, ex=ttl)
        except redis.exceptions.RedisError:
            pass

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }