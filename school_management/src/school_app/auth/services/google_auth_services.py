import os
from flask import current_app
from google.oauth2 import id_token
from google.auth.transport import requests
from school_app.extensions import db
from school_app.models.user import User
from school_app.auth.services.login import issue_tokens


def verify_google_token(credential):
    if not credential:
        return None, "Missing Google credential token"

    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return None, "Google Client ID is not configured on the server"

    try:
        google_data = id_token.verify_oauth2_token(
            credential, 
            requests.Request(), 
            client_id 
        )
        return google_data, None
    except ValueError:
        return None, "Invalid or expired Google token"

def find_or_create_google_user(google_data):
    google_id = google_data.get("sub")
    email = google_data.get("email")

    # 1. Existing user with this Google account
    user = User.query.filter_by(google_id=google_id).first()
    if user:
        return user

    # 2. Existing user who previously registered with standard email/password
    user = User.query.filter_by(email=email).first()
    if user:
        user.google_id = google_id
        db.session.commit()
        return user

    # 3. Completely new user: Generate a unique username under 30 chars
    base_username = email.split("@")[0][:20]
    username = base_username
    counter = 1

    while User.query.filter_by(username=username).first():
        username = f"{base_username}_{counter}"
        counter += 1

    new_user = User(
        email=email,
        username=username,
        google_id=google_id,
        password=None, 
    )

    db.session.add(new_user)
    db.session.commit()
    return new_user


def authenticate_google_user(payload):
    """Main service layer workflow called by the Flask route."""
    credential = payload.get("credential") if payload else None
    google_data, error = verify_google_token(credential)

    if error:
        return {"error": error}, 401

    user = find_or_create_google_user(google_data)
    tokens = issue_tokens(user) 

    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
        },
        **tokens,
    }, 200