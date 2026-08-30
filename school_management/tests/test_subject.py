# test/test_subject.py

def test_create_subject_success(client, admin_headers):
    payload = {"name": "Physics", "code": "PHYS101", "description": "Intro physics"}
    # Use json=payload instead of data=payload so Flask sends a JSON payload for Pydantic validation
    response = client.post("/subjects/create", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Physics"
    assert data["code"] == "PHYS101"


def test_create_subject_missing_required_field(client, admin_headers):
    """Validation failure with Pydantic returns a JSON 400 Bad Request."""
    payload = {"description": "No name or code"}
    # Use json=payload here as well
    response = client.post("/subjects/create", json=payload, headers=admin_headers)
    assert response.status_code == 400
    assert response.is_json


def test_get_subject_detail_success(client, admin_headers, subject):
    response = client.get(f"/subjects/{subject.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == subject.id


def test_get_subject_detail_not_found(client, admin_headers):
    """Confirms it resolves to a JSON 404 via the central error handler."""
    response = client.get("/subjects/99999", headers=admin_headers)
    assert response.status_code == 404


def test_get_all_subjects(client, admin_headers, subject):
    response = client.get("/subjects", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert any(s["id"] == subject.id for s in data)


def test_delete_subject_success(client, admin_headers, subject):
    response = client.delete(f"/subjects/{subject.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject deleted successfully"


def test_delete_subject_not_found(client, admin_headers):
    response = client.delete("/subjects/99999", headers=admin_headers)
    assert response.status_code == 404