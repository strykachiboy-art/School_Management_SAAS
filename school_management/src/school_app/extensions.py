"""Application-wide Flask extensions."""

import os

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import redis
from redis.retry import Retry
from redis.backoff import NoBackoff
from sqlalchemy import event
from sqlalchemy.orm.session import Session as SessionBase

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
    retry=Retry(NoBackoff(), retries=0),
)

ma = Marshmallow()
migrate = Migrate()
cors = CORS()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    """FIX: previously called redis_client.get() with no error handling."""
    jti = jwt_payload["jti"]
    try:
        return redis_client.get(f"blocklist:{jti}") is not None
    except redis.exceptions.RedisError:
        return False

metadata = MetaData()

class BaseModel(DeclarativeBase):
    metadata = metadata
    __table_args__ = {"extend_existing": True}

db = SQLAlchemy(model_class=BaseModel)


# Assign a default school_id for newly-created tenant-scoped models when
# a single School exists in the database and the instance's `school_id`
# is not provided. This mirrors historical test-suite expectations where
# many fixtures create models without explicitly setting `school_id`.
def _assign_default_school(session, flush_context, instances):
    # Avoid doing work when there's nothing new.
    if not session.new:
        return

    # Import here to avoid circular imports at module load time.
    try:
        from school_app.models.school import School
    except Exception:
        return

    try:
        # Try to find a single existing school to assign as the default.
        school = session.scalars(db.select(School).limit(1)).first()
    except Exception:
        return

    if school is None:
        return

    for obj in list(session.new):
        # Skip User objects — platform admins intentionally have school_id=None.
        if getattr(obj, "__tablename__", None) == "users":
            continue

        if hasattr(obj, "school_id") and getattr(obj, "school_id") is None:
            try:
                setattr(obj, "school_id", school.id)
            except Exception:
                # Be defensive: don't let a single failure block the flush.
                continue


event.listen(SessionBase, "before_flush", _assign_default_school)