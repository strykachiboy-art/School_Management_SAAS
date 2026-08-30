import pytest

def test_create_section(client, admin_auth_headers):
    """Test creating a section as an admin under a valid academic level."""
    # Setup stage and level first
    stage_res = client.post("/academic-stages/create", json={"name": "Senior Secondary", "display_order": 1}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    level_res = client.post("/academic-levels/create", json={"name": "SS1", "stage_id": stage_id, "display_order": 1}, headers=admin_auth_headers)
    level_id = level_res.get_json()["id"]

    payload = {"name": "Science A", "level_id": level_id, "display_order": 1}
    response = client.post("/sections/create", json=payload, headers=admin_auth_headers)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Science A"
    assert data["level_id"] == level_id
    assert "id" in data


def test_get_all_sections(client, admin_auth_headers):
    """Test retrieving paginated sections with optional level filtering."""
    response = client.get("/sections", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert "total" in data


def test_get_single_section(client, admin_auth_headers):
    """Test fetching a specific section by ID and verifying 404 behavior."""
    stage_res = client.post("/academic-stages/create", json={"name": "Junior Secondary", "display_order": 2}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    level_res = client.post("/academic-levels/create", json={"name": "JSS1", "stage_id": stage_id}, headers=admin_auth_headers)
    level_id = level_res.get_json()["id"]

    create_res = client.post("/sections/create", json={"name": "Gold", "level_id": level_id}, headers=admin_auth_headers)
    section_id = create_res.get_json()["id"]

    # Fetch successfully
    response = client.get(f"/sections/{section_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == section_id

    # Test 404 for non-existent ID
    missing_response = client.get("/sections/99999", headers=admin_auth_headers)
    assert missing_response.status_code == 404


def test_update_section(client, admin_auth_headers):
    """Test updating an existing section."""
    stage_res = client.post("/academic-stages/create", json={"name": "Primary", "display_order": 3}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    level_res = client.post("/academic-levels/create", json={"name": "Primary 1", "stage_id": stage_id}, headers=admin_auth_headers)
    level_id = level_res.get_json()["id"]

    create_res = client.post("/sections/create", json={"name": "Emerald", "level_id": level_id}, headers=admin_auth_headers)
    section_id = create_res.get_json()["id"]

    # Update section name
    response = client.put(f"/sections/{section_id}/edit", json={"name": "Emerald Updated"}, headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["name"] == "Emerald Updated"


def test_delete_section(client, admin_auth_headers):
    """Test deleting a section."""
    stage_res = client.post("/academic-stages/create", json={"name": "Nursery", "display_order": 4}, headers=admin_auth_headers)
    stage_id = stage_res.get_json()["id"]

    level_res = client.post("/academic-levels/create", json={"name": "Nursery 1", "stage_id": stage_id}, headers=admin_auth_headers)
    level_id = level_res.get_json()["id"]

    create_res = client.post("/sections/create", json={"name": "Ruby", "level_id": level_id}, headers=admin_auth_headers)
    section_id = create_res.get_json()["id"]

    # Delete section
    response = client.delete(f"/sections/{section_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Section deleted successfully"

    # Verify it is removed
    get_res = client.get(f"/sections/{section_id}", headers=admin_auth_headers)
    assert get_res.status_code == 404