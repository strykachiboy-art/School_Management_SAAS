import pytest
from unittest.mock import patch
from school_app.models.user import User

# --- Pytest Fixtures ---

@pytest.fixture
def test_client(app):
    """Provides a test client for sending HTTP requests."""
    return app.test_client()

@pytest.fixture
def mock_google_payload():
    """Sample payload returned by Google on successful token verification."""
    return {
        "sub": "google-uid-12345",
        "email": "student@example.com",
        "email_verified": True,
        "name": "Test Student"
    }


# --- Tests ---

class TestGoogleLoginRoute:

    @patch("school_app.auth.services.google_auth_services.id_token.verify_oauth2_token")
    def test_google_login_success_new_user(self, mock_verify, test_client, db, mock_google_payload):
        """Tests registration and login for a brand new Google user."""
        mock_verify.return_value = mock_google_payload

        response = test_client.post("/auth/google", json={"credential": "fake_valid_google_jwt"})
        data = response.get_json()

        assert response.status_code == 200
        assert data["message"] == "Login successful"
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "student@example.com"
        assert data["user"]["username"] == "student"

        user = User.query.filter_by(google_id="google-uid-12345").first()
        assert user is not None
        assert user.email == "student@example.com"

    @patch("school_app.auth.services.google_auth_services.id_token.verify_oauth2_token")
    def test_google_login_success_existing_email(self, mock_verify, test_client, db, mock_google_payload):
        """Tests linking google_id to an existing account registered via standard email."""
        existing_user = User(
            username="existing_student",
            email="student@example.com",
            password="hashed_password",
            google_id=None
        )
        db.session.add(existing_user)
        db.session.commit()

        mock_verify.return_value = mock_google_payload

        response = test_client.post("/auth/google", json={"credential": "fake_valid_google_jwt"})
        data = response.get_json()

        assert response.status_code == 200
        assert data["user"]["id"] == existing_user.id

        # Confirm google_id was updated on the existing record
        updated_user = db.session.get(User, existing_user.id)
        assert updated_user.google_id == "google-uid-12345"

    @patch("school_app.auth.services.google_auth_services.id_token.verify_oauth2_token")
    def test_google_login_invalid_token(self, mock_verify, test_client):
        """Tests route response when Google token is invalid or expired."""
        mock_verify.side_effect = ValueError("Token expired")

        response = test_client.post("/auth/google", json={"credential": "invalid_jwt_token"})
        data = response.get_json()

        assert response.status_code == 401
        assert data["error"] == "Invalid or expired Google token"

    def test_google_login_missing_credential(self, test_client):
        """Tests route response when the payload contains no credential key."""
        response = test_client.post("/auth/google", json={})
        data = response.get_json()

        assert response.status_code == 401
        assert data["error"] == "Missing Google credential token"

    def test_google_login_empty_body(self, test_client):
        """Tests route response when request body is empty."""
        response = test_client.post("/auth/google")
        data = response.get_json()

        assert response.status_code == 401
        assert data["error"] == "Missing Google credential token"