# test/test_register_route.py
import pytest

from school_app.extensions import db
from school_app.models.user import User


class TestRegister:
    def test_register_success(self, client):
        payload = {
            "username": "new_student",
            "email": "new_student@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201

        body = resp.get_json()
        assert body["message"] == "Registration successful"
        assert body["user"]["username"] == "new_student"
        assert body["user"]["email"] == "new_student@example.com"
        assert body["user"]["role"] == "student"
        assert "password" not in body["user"]

    def test_register_forces_student_role(self, client):
        payload = {
            "username": "sneaky_admin",
            "email": "sneaky@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
            "role": "admin",  # attempt to inject a role — should be ignored
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        assert resp.get_json()["user"]["role"] == "student"

    def test_register_duplicate_username(self, client, app):
        with app.app_context():
            existing = User(
                username="taken_name",
                email="original@example.com",
                password="hashed-placeholder",
                role="student",
            )
            db.session.add(existing)
            db.session.commit()

        payload = {
            "username": "taken_name",
            "email": "different@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Username already taken"

    def test_register_duplicate_email(self, client, app):
        with app.app_context():
            existing = User(
                username="original_user",
                email="taken@example.com",
                password="hashed-placeholder",
                role="student",
            )
            db.session.add(existing)
            db.session.commit()

        payload = {
            "username": "different_user",
            "email": "taken@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Email already registered"

    def test_register_password_mismatch(self, client):
        payload = {
            "username": "mismatch_user",
            "email": "mismatch@example.com",
            "password": "ValidPass123",
            "confirm_password": "DifferentPass456",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "Validation failed" in resp.get_json()["error"]

    def test_register_password_too_short(self, client):
        payload = {
            "username": "short_pw_user",
            "email": "shortpw@example.com",
            "password": "short",
            "confirm_password": "short",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "Validation failed" in resp.get_json()["error"]

    def test_register_username_too_short(self, client):
        payload = {
            "username": "ab",
            "email": "shortname@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "Validation failed" in resp.get_json()["error"]

    def test_register_invalid_email(self, client):
        payload = {
            "username": "bad_email_user",
            "email": "not-an-email",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
        }

        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 400
        assert "Validation failed" in resp.get_json()["error"]

    def test_register_missing_fields(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 400
        assert "Validation failed" in resp.get_json()["error"]

    def test_register_stores_hashed_password(self, client, app):
        payload = {
            "username": "hash_check_user",
            "email": "hashcheck@example.com",
            "password": "ValidPass123",
            "confirm_password": "ValidPass123",
        }

        client.post("/auth/register", json=payload)

        with app.app_context():
            user = User.query.filter_by(username="hash_check_user").first()
            assert user is not None
            assert user.password != "ValidPass123"  # must be hashed, not raw