# App/auth/services/logout.py
import time

from school_app.extensions import redis_client

def revoke_token(jti: str, exp: int) -> None:
    """Add a JWT's jti to the Redis blocklist until its natural expiry."""
    ttl = exp - int(time.time())

    if ttl > 0:
        redis_client.set(f"blocklist:{jti}", "revoked", ex=ttl)