from flask_jwt_extended import create_access_token
from school_app.extensions import redis_client


def refresh_access_token(user_id: str, current_jti: str, role: str) -> tuple[str | None, str | None]:
    
    # Validates the refresh token against Redis whitelist and issues a new access token.
    # Returns (new_access_token, None) on success, or (None, error_message) on failure.
    
    # 1. Fetch whitelisted JTI from Redis
    cached_jti = redis_client.get(f"refresh_whitelist:{user_id}")

    # 2. Convert from bytes if Redis returned a string/bytes object
    if isinstance(cached_jti, bytes):
        cached_jti = cached_jti.decode("utf-8")

    # 3. Check if the refresh token is valid and active in the whitelist
    if cached_jti is None or cached_jti != current_jti:
        return None, "Refresh token is invalid, expired, or has been revoked."

    # 4. Issue a new access token
    new_access_token = create_access_token(
        identity=str(user_id),
        additional_claims={"role": role} if role else {}
    )

    return new_access_token, None