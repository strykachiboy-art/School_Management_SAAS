# tests/test_academic_session.py

import uuid
from datetime import datetime, timezone

def _iso_date(date_str: str) -> str:
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc).isoformat()

def _session_payload(name=None):
    """
    Return a payload for creating an academic session.
    By default this produces a unique name to avoid accidental duplicates
    during test runs.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    return {
        "name": name or f"Session {unique_suffix}",
        "start_date": _iso_date("2026-09-01"),
        "end_date": _iso_date("2027-06-01"),
    }


def _create_session(client, admin_headers, name=None):
    payload = _session_payload(name)
    response = client.post("/academic-sessions/create", json=payload, headers=admin_headers)
    if response.status_code != 201:
        # Helpful debug output in test logs when creation fails
        print("DEBUG: create payload:", payload)
        print("DEBUG: response status:", response.status_code)
        try:
            print("DEBUG: response json:", response.get_json())
        except Exception:
            print("DEBUG: response data:", response.data)
    assert response.status_code == 201, f"Failed to create session in test helper: {response.get_json()}"
    return response.get_json()


def test_create_academic_session_success(client, admin_headers):
    payload = _session_payload()
    response = client.post("/academic-sessions/create", json=payload, headers=admin_headers)
    if response.status_code != 201:
        print("DEBUG create failed:", response.status_code, response.get_json() or response.data)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == payload["name"]
    assert data.get("is_active", False) is False
    assert "id" in data


def test_create_academic_session_duplicate_name(client, admin_headers):
    # create first
    _create_session(client, admin_headers, name="Dup Session")
    # attempt duplicate
    payload = _session_payload(name="Dup Session")
    response = client.post("/academic-sessions/create", json=payload, headers=admin_headers)
    # Accept either 400 with validation message or 409 if your app uses that code for duplicates.
    assert response.status_code in (400, 409)


def test_get_academic_session_success(client, admin_headers):
    created = _create_session(client, admin_headers)
    response = client.get(f"/academic-sessions/{created['id']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == created["id"]


def test_get_academic_session_not_found(client, admin_headers):
    response = client.get("/academic-sessions/99999", headers=admin_headers)
    assert response.status_code == 404


def test_get_all_academic_sessions(client, admin_headers):
    _create_session(client, admin_headers, name="List Session")
    response = client.get("/academic-sessions", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert any(s["name"] == "List Session" for s in data["items"])


def test_update_academic_session_success(client, admin_headers):
    created = _create_session(client, admin_headers, name="Old Name")
    response = client.patch(
        f"/academic-sessions/{created['id']}/edit",
        json={"name": "New Name"},
        headers=admin_headers,
    )
    if response.status_code != 200:
        print("DEBUG update failed:", response.status_code, response.get_json() or response.data)
    assert response.status_code == 200
    assert response.get_json()["name"] == "New Name"


def test_update_academic_session_not_found(client, admin_headers):
    response = client.patch(
        "/academic-sessions/99999/edit",
        json={"name": "New Name"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_delete_academic_session_success(client, admin_headers):
    created = _create_session(client, admin_headers)
    response = client.delete(f"/academic-sessions/{created['id']}", headers=admin_headers)
    if response.status_code != 200:
        print("DEBUG delete failed:", response.status_code, response.get_json() or response.data)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Academic session deleted successfully"


def test_delete_academic_session_not_found(client, admin_headers):
    response = client.delete("/academic-sessions/99999", headers=admin_headers)
    assert response.status_code == 404


def test_activate_academic_session_success(client, admin_headers):
    created = _create_session(client, admin_headers)
    response = client.patch(f"/academic-sessions/{created['id']}/activate", headers=admin_headers)
    if response.status_code != 200:
        print("DEBUG activate failed:", response.status_code, response.get_json() or response.data)
    assert response.status_code == 200
    assert response.get_json()["is_active"] is True


def test_activate_academic_session_deactivates_others(client, admin_headers):
    first = _create_session(client, admin_headers, name="Session A")
    second = _create_session(client, admin_headers, name="Session B")

    client.patch(f"/academic-sessions/{first['id']}/activate", headers=admin_headers)
    client.patch(f"/academic-sessions/{second['id']}/activate", headers=admin_headers)

    check_first = client.get(f"/academic-sessions/{first['id']}", headers=admin_headers)
    assert check_first.get_json()["is_active"] is False


def test_activate_academic_session_not_found(client, admin_headers):
    response = client.patch("/academic-sessions/99999/activate", headers=admin_headers)
    assert response.status_code == 404
