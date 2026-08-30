# App/auth/routes/forgot_password.py
from flask import jsonify
from school_app.auth.auth import auth_bp
from school_app.auth.services.forgot_password import request_password_reset, reset_password
from school_app.auth.request.forgot_password import ForgotPasswordRequest, ResetPasswordRequest
from school_app.utils.helpers import validate_request
from school_app.extensions import limiter


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per minute")
@validate_request(ForgotPasswordRequest)
def forgot_password(payload: ForgotPasswordRequest):
    request_password_reset(payload.email)
    return jsonify({
        "message": "If that email is registered, a reset link has been sent."
    }), 200



@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per minute")
@validate_request(ResetPasswordRequest)
def reset_password_route(payload: ResetPasswordRequest):
    success = reset_password(payload.token, payload.new_password)
    if not success:
        return jsonify({"error": "Invalid or expired reset token"}), 400
    return jsonify({"message": "Password has been reset successfully"}), 200