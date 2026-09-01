# App/auth/routes/register.py
from flask import jsonify
from school_app.auth.auth import auth_bp
from school_app.auth.services.register import register_user
from school_app.auth.request.register import RegisterRequest
from school_app.schemas.profile import ProfileSchema
from school_app.utils.helpers import validate_request
from school_app.extensions import limiter


profile_schema = ProfileSchema()


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("3 per minute")
@validate_request(RegisterRequest)
def register(payload: RegisterRequest):
    user, error = register_user(
        payload.username,
        payload.email,
        payload.password,
        school_id=payload.school_id,
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Registration successful",
        "user": profile_schema.dump(user),
    }), 201