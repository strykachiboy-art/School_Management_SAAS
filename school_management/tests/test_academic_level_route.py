import uuid
import pytest


# ====================================== CREATE ===============================================

def test_create_academic_level_success(client, admin_auth_headers, admin_stage):
    """Test POST /academic-levels/create - Success."""
    payload = {
        "stage_id": admin_stage.id,
        "name": f"Level {uuid.uuid4().hex[:6]}",
        "display_order": 1,
    }

    response = client.post(
        "/academic-levels/create",
        json=payload,
        headers=admin_auth_headers,
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == payload["name"]
    assert data["stage_id"] == payload["stage_id"]
    assert data["display_order"] == payload["display_order"]
    assert "id" in data


def test_create_academic_level_duplicate_name_fails(client, admin_auth_headers, admin_stage):
    """Test POST /academic-levels/create - Duplicate name within stage returns 400."""
    level_name = f"Level {uuid.uuid4().hex[:6]}"
    payload = {
        "stage_id": admin_stage.id,
        "name": level_name,
        "display_order": 1,
    }

    # Initial creation succeeds
    res1 = client.post("/academic-levels/create", json=payload, headers=admin_auth_headers)
    assert res1.status_code == 201

    # Duplicate creation fails
    res2 = client.post("/academic-levels/create", json=payload, headers=admin_auth_headers)
    assert res2.status_code == 400
    assert "Could not create academic level" in res2.get_json()["description"]


def test_create_academic_level_stage_not_found(client, admin_auth_headers):
    """Test POST /academic-levels/create - Invalid stage returns 404."""
    payload = {
        "stage_id": 999999,
        "name": f"Level {uuid.uuid4().hex[:6]}",
        "display_order": 1,
    }

    response = client.post(
        "/academic-levels/create",
        json=payload,
        headers=admin_auth_headers,
    )

    assert response.status_code == 404


# ====================================== READ ===============================================

def test_get_all_academic_levels(client, admin_auth_headers, admin_stage):
    """Test GET /academic-levels - List and pagination structure."""
    response = client.get("/academic-levels", headers=admin_auth_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "page" in data
    assert "pages" in data
    assert "total" in data


def test_get_academic_level_by_id(client, admin_auth_headers, admin_stage):
    """Test GET /academic-levels/<id> - Fetch single level."""
    # Create level first
    create_res = client.post(
        "/academic-levels/create",
        json={"stage_id": admin_stage.id, "name": f"Level {uuid.uuid4().hex[:6]}"},
        headers=admin_auth_headers,
    )
    level_id = create_res.get_json()["id"]

    response = client.get(f"/academic-levels/{level_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == level_id


def test_get_academic_level_not_found(client, admin_auth_headers):
    """Test GET /academic-levels/<id> - Non-existent ID returns 404."""
    response = client.get("/academic-levels/999999", headers=admin_auth_headers)
    assert response.status_code == 404


# ====================================== UPDATE ===============================================

def test_update_academic_level(client, admin_auth_headers, admin_stage):
    """Test PUT /academic-levels/<id>/edit - Update level details."""
    create_res = client.post(
        "/academic-levels/create",
        json={"stage_id": admin_stage.id, "name": f"Level {uuid.uuid4().hex[:6]}"},
        headers=admin_auth_headers,
    )
    level_id = create_res.get_json()["id"]

    update_payload = {"name": "Updated Level Name", "display_order": 5}
    response = client.put(
        f"/academic-levels/{level_id}/edit",
        json=update_payload,
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Updated Level Name"
    assert data["display_order"] == 5


# ====================================== DELETE ===============================================

def test_delete_academic_level(client, admin_auth_headers, admin_stage):
    """Test DELETE /academic-levels/<id> - Remove level."""
    create_res = client.post(
        "/academic-levels/create",
        json={"stage_id": admin_stage.id, "name": f"Level {uuid.uuid4().hex[:6]}"},
        headers=admin_auth_headers,
    )
    level_id = create_res.get_json()["id"]

    response = client.delete(f"/academic-levels/{level_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Academic level deleted successfully"