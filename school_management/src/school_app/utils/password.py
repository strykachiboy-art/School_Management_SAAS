from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password: str) -> str:
    
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")

    try:
        if current_app and current_app.config.get("TESTING"):
            return generate_password_hash(password, method="pbkdf2:sha256:1000")
    except RuntimeError:
        pass  

    return generate_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a stored password hash.

    :param plain_password: Cleartext password provided by the user
    :param hashed_password: Stored password hash from the database
    :return: True if match, False otherwise
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False

    if not plain_password or not hashed_password:
        return False

    try:
        return check_password_hash(hashed_password, plain_password)
    except (ValueError, TypeError):
        return False