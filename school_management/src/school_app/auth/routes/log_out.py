# App/auth/routes/logout.py
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

from school_app.auth.auth import auth_bp
from school_app.auth.services.log_out import revoke_token


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    token = get_jwt()
    revoke_token(token["jti"], token["exp"])
    return jsonify({"message": "Successfully logged out"}), 200