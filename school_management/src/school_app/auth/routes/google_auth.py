from school_app.auth.auth import auth_bp
from flask import Blueprint, request, jsonify
from school_app.extensions import limiter 
from school_app.auth.services.google_auth_services import authenticate_google_user  


@auth_bp.route("/google", methods=["POST"])
@limiter.limit("5 per minute")
def google_login():
    payload = request.get_json(silent=True) or {}
    response_data, status_code = authenticate_google_user(payload)
    return jsonify(response_data), status_code