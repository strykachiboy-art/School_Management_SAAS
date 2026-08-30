from flask import request
from functools import wraps
from pydantic import ValidationError


def wants_json():
    return (
        request.is_json
        or request.accept_mimetypes["application/json"]
        >= request.accept_mimetypes["text/html"]
    )


def validate_request(schema=None):
    """A decorator to validate incoming JSON request data against a Pydantic schema."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            raw_data = request.get_json(silent=True) or {}

            if schema:
                validated = schema.model_validate(raw_data)  # ValidationError now bubbles up
                return f(validated, *args, **kwargs)

            return f(*args, **kwargs)
        return decorated_function
    return decorator