from school_app.models.user import User


# ============================ GET /auth/profile ============================

def test_get_profile_returns_current_user(client, student_headers, student):
    """A logged-in user can fetch their own profile via the route."""
    res = client.get("/auth/profile", headers=student_headers)

    assert res.status_code == 200
    assert res.json["id"] == student.user_id
    assert res.json["role"] == "student"
    assert "password" not in res.json


def test_get_profile_requires_auth(client):
    """No Authorization header -> request is rejected before reaching the view."""
    res = client.get("/auth/profile", headers={"Accept": "application/json"})

    assert res.status_code == 401


# ============================ PATCH /auth/profile ============================

def test_update_profile_route_success(client, student_headers, student):
    """PATCH updates username/email through the full route + service + DB path."""
    res = client.patch(
        "/auth/profile",
        json={"username": "brand_new_name", "email": "brandnew@example.com"},
        headers=student_headers,
    )

    assert res.status_code == 200
    assert res.json["username"] == "brand_new_name"
    assert res.json["email"] == "brandnew@example.com"


def test_update_profile_route_partial_update(client, student_headers):
    """Omitting a field in the PATCH body leaves it unchanged."""
    original = client.get("/auth/profile", headers=student_headers).json
    original_username = original["username"]

    res = client.patch(
        "/auth/profile",
        json={"email": "onlyemail@example.com"},
        headers=student_headers,
    )

    assert res.status_code == 200
    assert res.json["email"] == "onlyemail@example.com"
    assert res.json["username"] == original_username


def test_update_profile_route_duplicate_username(client, student_headers, make_user):
    """Route surfaces the service's ValueError as a client-facing error, not a 500."""
    other_user = make_user("existing")

    res = client.patch(
        "/auth/profile",
        json={"username": other_user.username},
        headers=student_headers,
    )

    assert res.status_code in (400, 409)


def test_update_profile_route_requires_auth(client):
    """No Authorization header -> PATCH is rejected before reaching the view."""
    res = client.patch(
        "/auth/profile",
        json={"username": "whoever"},
        headers={"Accept": "application/json"},
    )

    assert res.status_code == 401