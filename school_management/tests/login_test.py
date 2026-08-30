# test/test_login_route.py
import pytest

from school_app.extensions import db, redis_client
from school_app.models.user import User
from school_app.utils.password import hash_password


@pytest.fixture
def login_user(app):
    with app.app_context():
        user = User(
            username="login_test_user",
            email="login_test@example.com",
            password=hash_password("CorrectPass123"),
            role="student",
        )
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture(autouse=True)
def clear_redis_whitelist():
    yield
    for key in redis_client.keys("refresh_whitelist:*"):
        redis_client.delete(key)


class TestLogin:
    def test_login_success(self, client, login_user):
        resp = client.post(
            "/auth/login",
            json={"email": login_user.email, "password": "CorrectPass123"},
        )
        assert resp.status_code == 200

        body = resp.get_json()
        assert body["message"] == "Login successful"
        assert "access_token" in body
        assert "refresh_token" in body

    def test_login_wrong_password(self, client, login_user):
        resp = client.post(
            "/auth/login",
            json={"email": login_user.email, "password": "WrongPassword"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "Invalid email or password"

    def test_login_nonexistent_email(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "whatever123"},
        )
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "Invalid email or password"

    def test_login_invalid_email_format(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "not-an-email", "password": "whatever123"},
        )
        assert resp.status_code == 400

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 400

    def test_login_email_normalized(self, client, login_user):
        resp = client.post(
            "/auth/login",
            json={"email": login_user.email.upper(), "password": "CorrectPass123"},
        )
        assert resp.status_code == 200

    def test_login_sets_refresh_whitelist(self, client, login_user):
        client.post(
            "/auth/login",
            json={"email": login_user.email, "password": "CorrectPass123"},
        )

        with client.application.app_context():
            key = f"refresh_whitelist:{login_user.id}"
            assert redis_client.get(key) is not None

    def test_login_overwrites_previous_whitelist_entry(self, client, login_user):
        # login twice — second login should overwrite, not duplicate
        client.post(
            "/auth/login",
            json={"email": login_user.email, "password": "CorrectPass123"},
        )
        first_jti = redis_client.get(f"refresh_whitelist:{login_user.id}")

        client.post(
            "/auth/login",
            json={"email": login_user.email, "password": "CorrectPass123"},
        )
        second_jti = redis_client.get(f"refresh_whitelist:{login_user.id}")

        assert first_jti != second_jti