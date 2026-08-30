import pytest

def test_create_academic_stage(client, admin_auth_headers):
    """Test creating an academic stage as an admin."""
    payload = {"name": "Senior Secondary", "code": "SS"}
    response = client.post("/academic-stages/create", json=payload, headers=admin_auth_headers)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Senior Secondary"
    assert "id" in data


def test_get_all_academic_stages(client, admin_auth_headers):
    """Test retrieving paginated academic stages."""
    response = client.get("/academic-stages", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data


def test_get_single_academic_stage(client, admin_auth_headers):
    """Test fetching a specific academic stage by ID, and handling 404."""
    # 1. Create one first to ensure it exists
    create_res = client.post("/academic-stages/create", json={"name": "Junior Secondary", "code": "JS"}, headers=admin_auth_headers)
    stage_id = create_res.get_json()["id"]

    # 2. Fetch it successfully
    response = client.get(f"/academic-stages/{stage_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == stage_id

    # 3. Test 404 for non-existent ID
    missing_response = client.get("/academic-stages/99999", headers=admin_auth_headers)
    assert missing_response.status_code == 404


def test_update_academic_stage(client, admin_auth_headers):
    """Test updating an existing academic stage."""
    create_res = client.post("/academic-stages/create", json={"name": "Primary", "code": "PRI"}, headers=admin_auth_headers)
    stage_id = create_res.get_json()["id"]

    # Update the stage
    response = client.put(f"/academic-stages/{stage_id}/edit", json={"name": "Primary School Updated"}, headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Primary School Updated"


def test_delete_academic_stage(client, admin_auth_headers):
    """Test deleting an academic stage."""
    create_res = client.post("/academic-stages/create", json={"name": "Nursery", "num_code": 0}, headers=admin_auth_headers)
    stage_id = create_res.get_json()["id"]

    # Delete the stage
    response = client.delete(f"/academic-stages/{stage_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Academic stage deleted successfully"

    # Verify it's gone (should return 404)
    get_res = client.get(f"/academic-stages/{stage_id}", headers=admin_auth_headers)
    assert get_res.status_code == 404