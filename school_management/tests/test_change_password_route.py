# test/test_change_password_route.py

from school_app.extensions import db
from school_app.models.user import User
from school_app.utils.password import verify_password

JSON_HEADERS = {"Accept": "application/json"}

def test_change_password_success(client, user_with_password):
    headers = user_with_password["headers"]
    payload = {
        "current_password": user_with_password["plain_password"],
        "new_password": "NewPassword456",
        "confirm_password": "NewPassword456",
    }

    response = client.patch("/auth/change_password", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.get_json()["success"] == "Password changed successfully"

    user = db.session.get(User, user_with_password["user_id"])
    assert verify_password("NewPassword456", user.password) is True
    assert verify_password(user_with_password["plain_password"], user.password) is False


def test_change_password_wrong_current_password(client, user_with_password):
    headers = user_with_password["headers"]
    payload = {
        "current_password": "TotallyWrongPassword",
        "new_password": "NewPassword456",
        "confirm_password": "NewPassword456",
    }

    response = client.patch("/auth/change_password", json=payload, headers=headers)
    assert response.status_code == 400
    assert "incorrect" in response.get_json()["error"].lower()


def test_change_password_same_as_current(client, user_with_password):
    """Schema-level check: raw current == raw new is rejected before hitting the service."""
    headers = user_with_password["headers"]
    payload = {
        "current_password": user_with_password["plain_password"],
        "new_password": user_with_password["plain_password"],
        "confirm_password": user_with_password["plain_password"],
    }

    response = client.patch("/auth/change_password", json=payload, headers=headers)
    assert response.status_code == 400
    assert "different" in response.get_json()["error"].lower()


def test_change_password_mismatched_confirmation(client, user_with_password):
    headers = user_with_password["headers"]
    payload = {
        "current_password": user_with_password["plain_password"],
        "new_password": "NewPassword456",
        "confirm_password": "SomethingElse789",
    }

    response = client.patch("/auth/change_password", json=payload, headers=headers)
    assert response.status_code == 400
    assert "match" in response.get_json()["error"].lower()


def test_change_password_too_short(client, user_with_password):
    headers = user_with_password["headers"]
    payload = {
        "current_password": user_with_password["plain_password"],
        "new_password": "short",
        "confirm_password": "short",
    }

    response = client.patch("/auth/change_password", json=payload, headers=headers)
    assert response.status_code == 400
    assert "new_password" in response.get_json()["error"]


def test_change_password_missing_field(client, user_with_password):
    headers = user_with_password["headers"]
    payload = {
        "current_password": user_with_password["plain_password"],
        "new_password": "NewPassword456",
        # confirm_password omitted
    }

    response = client.patch("/auth/change_password", json=payload, headers=headers)
    assert response.status_code == 400
    assert "confirm_password" in response.get_json()["error"]


def test_change_password_requires_auth(client):
    payload = {
        "current_password": "whatever",
        "new_password": "whatever123",
        "confirm_password": "whatever123",
    }
    response = client.patch("/auth/change_password", json=payload)
    assert response.status_code in (401, 403)