from datetime import datetime, timedelta


def _session_payload(name="2026 Session"):
    start = datetime(2026, 1, 1)
    end = datetime(2026, 12, 31)
    return {
        "name": name,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }


def _create_session(client, admin_headers, name="2026 Session"):
    response = client.post("/academic-sessions/create", json=_session_payload(name), headers=admin_headers)
    return response.get_json()


def test_create_academic_session_success(client, admin_headers):
    response = client.post("/academic-sessions/create", json=_session_payload(), headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "2026 Session"
    assert data["is_active"] is False


def test_create_academic_session_duplicate_name(client, admin_headers):
    _create_session(client, admin_headers, name="Dup Session")
    response = client.post("/academic-sessions/create", json=_session_payload(name="Dup Session"), headers=admin_headers)
    assert response.status_code == 400


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
    assert any(s["name"] == "List Session" for s in data["items"])


def test_update_academic_session_success(client, admin_headers):
    created = _create_session(client, admin_headers, name="Old Name")
    response = client.patch(
        f"/academic-sessions/{created['id']}/edit",
        json={"name": "New Name"},
        headers=admin_headers,
    )
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
    assert response.status_code == 200
    assert response.get_json()["message"] == "Academic session deleted successfully"


def test_delete_academic_session_not_found(client, admin_headers):
    response = client.delete("/academic-sessions/99999", headers=admin_headers)
    assert response.status_code == 404


def test_activate_academic_session_success(client, admin_headers):
    created = _create_session(client, admin_headers)
    response = client.patch(f"/academic-sessions/{created['id']}/activate", headers=admin_headers)
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