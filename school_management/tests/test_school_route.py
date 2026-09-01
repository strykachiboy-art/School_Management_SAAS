from school_app.extensions import db
from school_app.models.school import School


# ======================================================================
# CREATE
# ======================================================================

def test_create_school_route_success(
    client,
    platform_admin_headers,
):
    response = client.post(
        "/schools/create",
        json={
            "name": "Route School",
            "slug": "route-school",
            "country": "Nigeria",
            "timezone": "Africa/Lagos",
            "currency": "NGN",
            "locale": "en-NG",
        },
        headers=platform_admin_headers,
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["name"] == "Route School"
    assert data["slug"] == "route-school"


def test_create_school_route_duplicate_slug(
    client,
    platform_admin_headers,
    school,
):
    response = client.post(
        "/schools/create",
        json={
            "name": "Duplicate School",
            "slug": school.slug,
            "country": "Nigeria",
            "timezone": "Africa/Lagos",
            "currency": "NGN",
            "locale": "en-NG",
        },
        headers=platform_admin_headers,
    )

    assert response.status_code == 400


def test_create_school_route_requires_auth(client):
    response = client.post(
        "/schools/create",
        json={
            "name": "Unauthorized School",
            "slug": "unauthorized-school",
            "country": "Nigeria",
            "timezone": "Africa/Lagos",
            "currency": "NGN",
            "locale": "en-NG",
        },
    )

    assert response.status_code in (401, 403)


# ======================================================================
# GET ALL
# ======================================================================

def test_get_all_schools_route_success(
    client,
    platform_admin_headers,
    school,
):
    response = client.get(
        "/schools",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert "items" in data
    assert "page" in data
    assert "pages" in data
    assert "total" in data

    assert any(
        item["id"] == school.id
        for item in data["items"]
    )


def test_get_all_schools_route_search(
    client,
    platform_admin_headers,
    school,
):
    response = client.get(
        "/schools?search=Test",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert any(
        item["id"] == school.id
        for item in data["items"]
    )


def test_get_all_schools_route_pagination(
    client,
    platform_admin_headers,
    school,
):
    response = client.get(
        "/schools?page=1&per_page=1",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["page"] == 1
    assert len(data["items"]) <= 1


def test_get_all_schools_route_include_inactive(
    client,
    platform_admin_headers,
    school,
):
    with client.application.app_context():
        school_db = db.session.get(
            School,
            school.id,
        )

        assert school_db is not None

        school_db.is_active = False
        db.session.commit()

    response = client.get(
        "/schools?include_inactive=true",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert any(
        item["id"] == school.id
        for item in data["items"]
    )


# ======================================================================
# GET SINGLE
# ======================================================================

def test_get_school_route_success(
    client,
    platform_admin_headers,
    school,
):
    response = client.get(
        f"/schools/{school.id}",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == school.id
    assert data["name"] == school.name
    assert data["slug"] == school.slug


def test_get_school_route_not_found(
    client,
    platform_admin_headers,
):
    response = client.get(
        "/schools/999999",
        headers=platform_admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# GET BY SLUG
# ======================================================================

def test_get_school_by_slug_route_success(
    client,
    platform_admin_headers,
    school,
):
    response = client.get(
        f"/schools/by-slug/{school.slug}",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == school.id
    assert data["slug"] == school.slug


def test_get_school_by_slug_route_not_found(
    client,
    platform_admin_headers,
):
    response = client.get(
        "/schools/by-slug/does-not-exist",
        headers=platform_admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# UPDATE
# ======================================================================

def test_update_school_route_success(
    client,
    platform_admin_headers,
    school,
):
    response = client.patch(
        f"/schools/{school.id}/edit",
        json={
            "name": "Updated Route School",
            "country": "Nigeria",
            "timezone": "Africa/Lagos",
            "currency": "NGN",
            "locale": "en-NG",
        },
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == school.id
    assert data["name"] == "Updated Route School"


def test_update_school_route_not_found(
    client,
    platform_admin_headers,
):
    response = client.patch(
        "/schools/999999/edit",
        json={
            "name": "Missing School",
        },
        headers=platform_admin_headers,
    )

    assert response.status_code == 404


def test_update_school_route_requires_auth(
    client,
    school,
):
    response = client.patch(
        f"/schools/{school.id}/edit",
        json={
            "name": "Unauthorized Update",
        },
    )

    assert response.status_code in (401, 403)


# ======================================================================
# DELETE
# ======================================================================

def test_delete_school_route_success(
    client,
    platform_admin_headers,
):
    with client.application.app_context():
        school = School(
            name="Delete Route School",
            slug="delete-route-school",
        )

        db.session.add(school)
        db.session.commit()

        school_id = school.id

    response = client.delete(
        f"/schools/{school_id}",
        headers=platform_admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "School deleted successfully"

    with client.application.app_context():
        deleted = db.session.get(
            School,
            school_id,
        )

        assert deleted is None


def test_delete_school_route_not_found(
    client,
    platform_admin_headers,
):
    response = client.delete(
        "/schools/999999",
        headers=platform_admin_headers,
    )

    assert response.status_code == 404


def test_delete_school_route_with_users_is_rejected(
    client,
    platform_admin_headers,
    school,
    make_user,
):
    make_user(
        suffix="route_delete",
        role="student",
    )

    response = client.delete(
        f"/schools/{school.id}",
        headers=platform_admin_headers,
    )

    assert response.status_code == 400

    data = response.get_json()

    assert "Cannot delete school" in str(data)


def test_delete_school_route_requires_auth(
    client,
    school,
):
    response = client.delete(
        f"/schools/{school.id}",
    )

    assert response.status_code in (401, 403)