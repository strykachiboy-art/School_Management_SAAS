import pytest
from datetime import date
from school_app.extensions import db
from school_app.models.term import Term


# ----------------------------------------------------------------------
# Helper Fixture for Term Tests
# ----------------------------------------------------------------------

@pytest.fixture
def term(app, academic_session):
    with app.app_context():
        t = Term(
            name="First Term",
            start_date=date(2026, 9, 1),
            end_date=date(2026, 12, 15),
            is_current=False,  # or whatever attribute is defined on your model
            academic_session_id=academic_session.id,
        )
        db.session.add(t)
        db.session.commit()
        db.session.refresh(t)
        db.session.expunge(t)
        return t


# ----------------------------------------------------------------------
# 1. Create Term Tests (`POST /terms/create`)
# ----------------------------------------------------------------------

def test_create_term_success(json_client, admin_headers, academic_session):
    payload = {
        "name": "Second Term",
        "start_date": "2027-01-10",
        "end_date": "2027-04-15",
        "academic_session_id": academic_session.id,
    }
    response = json_client.post("/terms/create", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Second Term"
    assert data["academic_session_id"] == academic_session.id
    assert "id" in data


def test_create_term_unauthorized_for_non_admin(json_client, teacher_headers, academic_session):
    payload = {
        "name": "Third Term",
        "end_date": "2027-07-20",
        "academic_session_id": academic_session.id,
    }
    response = json_client.post("/terms/create", json=payload, headers=teacher_headers)
    assert response.status_code == 403


def test_create_term_invalid_blank_name(json_client, admin_headers, academic_session):
    payload = {
        "name": "   ",
        "end_date": "2027-04-15",
        "academic_session_id": academic_session.id,
    }
    response = json_client.post("/terms/create", json=payload, headers=admin_headers)
    assert response.status_code == 400


# ----------------------------------------------------------------------
# 2. Get All Terms Tests (`GET /terms`)
# ----------------------------------------------------------------------

def test_get_all_terms_success(json_client, teacher_headers, term):
    response = json_client.get("/terms", headers=teacher_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["items"][0]["name"] == term.name


def test_get_all_terms_with_search(json_client, teacher_headers, term):
    response = json_client.get("/terms?search=First", headers=teacher_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) == 1

    response_empty = json_client.get("/terms?search=NonExistent", headers=teacher_headers)
    assert response_empty.status_code == 200
    assert len(response_empty.get_json()["items"]) == 0


def test_get_all_terms_unauthorized_student(json_client, student_headers):
    response = json_client.get("/terms", headers=student_headers)
    assert response.status_code == 403


# ----------------------------------------------------------------------
# 3. Get Term By ID Tests (`GET /terms/<id>`)
# ----------------------------------------------------------------------

def test_get_term_by_id_success(json_client, teacher_headers, term):
    response = json_client.get(f"/terms/{term.id}", headers=teacher_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == term.id
    assert data["name"] == term.name


def test_get_term_by_id_not_found(json_client, teacher_headers):
    response = json_client.get("/terms/99999", headers=teacher_headers)
    assert response.status_code == 404


# ----------------------------------------------------------------------
# 4. Update Term Tests (`PUT/PATCH /terms/<id>/edit`)
# ----------------------------------------------------------------------

def test_update_term_success(json_client, admin_headers, term, academic_session):
    payload = {
        "name": "Updated Term Name",
        "end_date": "2026-12-20",
        "academic_session_id": academic_session.id,
    }
    response = json_client.patch(f"/terms/{term.id}/edit", json=payload, headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Updated Term Name"


def test_update_term_not_found(json_client, admin_headers, academic_session):
    payload = {
        "name": "Non-existent Term",
        "end_date": "2026-12-20",
        "academic_session_id": academic_session.id,
    }
    response = json_client.patch("/terms/99999/edit", json=payload, headers=admin_headers)
    assert response.status_code == 404


# ----------------------------------------------------------------------
# 5. Activate Term Tests (`PATCH /terms/<id>/activate`)
# ----------------------------------------------------------------------

def test_activate_term_success(json_client, admin_headers, term):
    response = json_client.patch(f"/terms/{term.id}/activate", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == term.id


def test_activate_term_not_found(json_client, admin_headers):
    response = json_client.patch("/terms/99999/activate", headers=admin_headers)
    assert response.status_code == 404


# ----------------------------------------------------------------------
# 6. Delete Term Tests (`DELETE /terms/<id>`)
# ----------------------------------------------------------------------

def test_delete_term_success(json_client, admin_headers, term):
    response = json_client.delete(f"/terms/{term.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Term deleted successfully"

    # Verify deletion via GET
    get_res = json_client.get(f"/terms/{term.id}", headers=admin_headers)
    assert get_res.status_code == 404


def test_delete_term_not_found(json_client, admin_headers):
    response = json_client.delete("/terms/99999", headers=admin_headers)
    assert response.status_code == 404