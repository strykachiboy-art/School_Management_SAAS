from school_app.auth.auth import auth_bp
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from school_app.auth.services.refresh_access_token import refresh_access_token
from school_app.extensions import limiter

@auth_bp.route("/refresh", methods = ["POST"])
@limiter.limit("10 per minute")
@jwt_required(refresh=True)  # <-- WE MUST HAVE refresh=True
def refresh():
    # 1. Extract values from decoded JWT payload
    user_id = get_jwt_identity()
    jwt_payload = get_jwt()
    current_jti = jwt_payload["jti"]
    role = jwt_payload.get("role")
    school_id = jwt_payload.get("school_id")

    # 2. Call service function
    new_token, error = refresh_access_token(
        user_id=user_id,
        current_jti=current_jti,
        role=role,
        school_id=school_id,
    )

    # 3. Handle errors
    if error:
        return jsonify({
            "status": "fail",
            "message": error
        }), 401

    # 4. Return success response
    return jsonify({
        "status": "success",
        "access_token": new_token
    }), 200