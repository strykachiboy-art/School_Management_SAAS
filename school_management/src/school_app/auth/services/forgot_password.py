import secrets
import hashlib

from school_app.utils.password import hash_password
from datetime import timedelta, timezone
from school_app.extensions import db
from school_app.models.user import User
from school_app.models.password_reset_token import PasswordResetToken, _utcnow

def request_password_reset(email: str) -> None:
    
    email = email.strip().lower()
    
    # find user
    user = User.query.filter_by(email = email).first()
    if user is None:
        return # silent no-op, wontv reveal users existence
    
    # invalidates any previous unused token for this user
    PasswordResetToken.query.filter_by(user_id = user.id, used = False).update({"used": True})
    
    # generate secure token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    #calculate expiry
    expires_at = _utcnow() + timedelta(minutes=15)
    
    reset_token = PasswordResetToken(
        user_id = user.id,
        token = token_hash,
        expires_at=expires_at,
        used=False
    )
    
    db.session.add(reset_token)
    db.session.commit()
    
    
    
def reset_password(raw_token: str, new_password: str) -> bool:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    reset_token = PasswordResetToken.query.filter_by(token=token_hash, used=False).first()

    if reset_token is None:
        return False

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < _utcnow():
        return False

    user = db.session.get(User, reset_token.user_id)
    if user is None:
        return False

    user.password = hash_password(new_password)
    reset_token.used = True

    db.session.commit()
    return True