import pytest

from school_app.extensions import db
from school_app.models.user import User
from school_app.models.password_reset_token import PasswordResetToken, _utcnow
from school_app.utils.password import hash_password
from datetime import timedelta

JSON_HEADERS = {"Accept": "application/json"}


@pytest.fixture
def user(app):
    with app.app_context():
        u = User(
            username="reset_test_user",
            email="reset_test@example.com",
            password=hash_password("OldPassword123"),
            role="student",
        )
        db.session.add(u)
        db.session.commit()
        yield u


class TestForgotPassword:
    def test_forgot_password_existing_email(self, client, user):
        resp = client.post(
            "/auth/forgot-password", json={"email": user.email}, headers=JSON_HEADERS
        )
        assert resp.status_code == 200

        with client.application.app_context():
            token = PasswordResetToken.query.filter_by(user_id=user.id).first()
            assert token is not None
            assert token.used is False

    def test_forgot_password_nonexistent_email_same_response(self, client):
        resp = client.post(
            "/auth/forgot-password",
            json={"email": "nobody@example.com"},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 200
        assert "message" in resp.get_json()

    def test_forgot_password_missing_email(self, client):
        resp = client.post("/auth/forgot-password", json={}, headers=JSON_HEADERS)
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body
        assert "Validation failed" in body["error"]

    def test_forgot_password_invalid_email_format(self, client):
        resp = client.post(
            "/auth/forgot-password",
            json={"email": "not-an-email"},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "Validation failed" in body["error"]

    def test_forgot_password_email_normalized(self, client, user):
        # mixed-case email should still match the stored lowercase one
        resp = client.post(
            "/auth/forgot-password",
            json={"email": user.email.upper()},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 200

        with client.application.app_context():
            token = PasswordResetToken.query.filter_by(user_id=user.id).first()
            assert token is not None

    def test_forgot_password_invalidates_previous_token(self, client, user):
        client.post(
            "/auth/forgot-password", json={"email": user.email}, headers=JSON_HEADERS
        )
        client.post(
            "/auth/forgot-password", json={"email": user.email}, headers=JSON_HEADERS
        )

        with client.application.app_context():
            tokens = PasswordResetToken.query.filter_by(user_id=user.id).all()
            used_tokens = [t for t in tokens if t.used]
            unused_tokens = [t for t in tokens if not t.used]
            assert len(used_tokens) == 1
            assert len(unused_tokens) == 1


class TestResetPassword:
    def test_reset_password_success(self, client, user):
        import secrets, hashlib

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        with client.application.app_context():
            rt = PasswordResetToken(
                user_id=user.id,
                token=token_hash,
                expires_at=_utcnow() + timedelta(minutes=15),
                used=False,
            )
            db.session.add(rt)
            db.session.commit()

        resp = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword123"},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 200

    def test_reset_password_invalid_token(self, client):
        resp = client.post(
            "/auth/reset-password",
            json={"token": "bogus-token", "new_password": "NewPassword123"},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Invalid or expired reset token"

    def test_reset_password_expired_token(self, client, user):
        import secrets, hashlib

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        with client.application.app_context():
            rt = PasswordResetToken(
                user_id=user.id,
                token=token_hash,
                expires_at=_utcnow() - timedelta(minutes=1),  # already expired
                used=False,
            )
            db.session.add(rt)
            db.session.commit()

        resp = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword123"},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Invalid or expired reset token"

    def test_reset_password_too_short(self, client, user):
        resp = client.post(
            "/auth/reset-password",
            json={"token": "whatever", "new_password": "short"},
            headers=JSON_HEADERS,
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "Validation failed" in body["error"]

    def test_reset_password_missing_fields(self, client):
        resp = client.post("/auth/reset-password", json={}, headers=JSON_HEADERS)
        assert resp.status_code == 400
        body = resp.get_json()
        assert "Validation failed" in body["error"]

    def test_reset_password_reused_token_fails(self, client, user):
        import secrets, hashlib

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        with client.application.app_context():
            rt = PasswordResetToken(
                user_id=user.id,
                token=token_hash,
                expires_at=_utcnow() + timedelta(minutes=15),
                used=False,
            )
            db.session.add(rt)
            db.session.commit()

        first = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "NewPassword123"},
            headers=JSON_HEADERS,
        )
        assert first.status_code == 200

        second = client.post(
            "/auth/reset-password",
            json={"token": raw_token, "new_password": "AnotherPassword456"},
            headers=JSON_HEADERS,
        )
        assert second.status_code == 400
        assert second.get_json()["error"] == "Invalid or expired reset token"