# App/auth/routes/login.py
from flask import jsonify

from school_app.auth.auth import auth_bp
from school_app.auth.services.login import authenticate_user, issue_tokens
from school_app.auth.request.login import LoginRequest
from school_app.utils.helpers import validate_request
from school_app.extensions import limiter


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
@validate_request(LoginRequest)
def login(payload: LoginRequest):
    user, error = authenticate_user(payload.email, payload.password)

    if error:
        return jsonify({"error": error}), 401

    tokens = issue_tokens(user)

    return jsonify({
        "message": "Login successful",
        **tokens,
    }), 200