import pytest

def test_create_academic_level(client, admin_auth_headers):
    """Test creating an academic level as an admin."""
    # First, let's create a stage so we have a valid stage_id foreign key reference
    stage_res = client.post("/academic-stages/create", json={"name": "Senior Secondary", "display_order": 1}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    payload = {"name": "SS1", "stage_id": stage_id, "display_order": 1}
    response = client.post("/academic-levels/create", json=payload, headers=admin_auth_headers)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "SS1"
    assert data["stage_id"] == stage_id
    assert "id" in data


def test_get_all_academic_levels(client, admin_auth_headers):
    """Test retrieving paginated academic levels with optional stage filtering."""
    response = client.get("/academic-levels", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data


def test_get_single_academic_level(client, admin_auth_headers):
    """Test fetching a specific academic level by ID and verifying 404 behavior."""
    stage_res = client.post("/academic-stages/create", json={"name": "Junior Secondary", "display_order": 2}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    create_res = client.post("/academic-levels/create", json={"name": "JSS1", "stage_id": stage_id}, headers=admin_auth_headers)
    level_id = create_res.get_json()["id"]

    # Fetch successfully
    response = client.get(f"/academic-levels/{level_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == level_id

    # Test 404 for non-existent ID
    missing_response = client.get("/academic-levels/99999", headers=admin_auth_headers)
    assert missing_response.status_code == 404


def test_update_academic_level(client, admin_auth_headers):
    """Test updating an existing academic level."""
    stage_res = client.post("/academic-stages/create", json={"name": "Primary School", "display_order": 3}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    create_res = client.post("/academic-levels/create", json={"name": "Primary 1", "stage_id": stage_id}, headers=admin_auth_headers)
    level_id = create_res.get_json()["id"]

    # Update level name
    response = client.put(f"/academic-levels/{level_id}/edit", json={"name": "Primary One Updated"}, headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Primary One Updated"


def test_delete_academic_level(client, admin_auth_headers):
    """Test deleting an academic level."""
    stage_res = client.post("/academic-stages/create", json={"name": "Nursery School", "display_order": 4}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    create_res = client.post("/academic-levels/create", json={"name": "Nursery 1", "stage_id": stage_id}, headers=admin_auth_headers)
    level_id = create_res.get_json()["id"]

    # Delete level
    response = client.delete(f"/academic-levels/{level_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Academic level deleted successfully"

    # Verify it is removed
    get_res = client.get(f"/academic-levels/{level_id}", headers=admin_auth_headers)
    assert get_res.status_code == 404