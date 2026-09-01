from flask_jwt_extended import create_access_token
from school_app.extensions import redis_client
import redis


def refresh_access_token(user_id: str, current_jti: str, role: str, school_id: int | None = None) -> tuple[str | None, str | None]:
    
    try:
        cached_jti = redis_client.get(f"refresh_whitelist:{user_id}")
    except redis.exceptions.RedisError:
        return None, "Unable to verify refresh token — please try again shortly."

    # 2. Convert from bytes if Redis returned a string/bytes object
    if isinstance(cached_jti, bytes):
        cached_jti = cached_jti.decode("utf-8")

    # 3. Check if the refresh token is valid and active in the whitelist
    if cached_jti is None or cached_jti != current_jti:
        return None, "Refresh token is invalid, expired, or has been revoked."

    # 4. Issue a new access token
    claims = {"role": role} if role else {}
    if school_id is not None:
        claims["school_id"] = school_id

    new_access_token = create_access_token(
        identity=str(user_id),
        additional_claims=claims,
    )

    return new_access_token, None