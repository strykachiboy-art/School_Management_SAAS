# test/test_classroom.py

from school_app.models.classroom import Classroom

JSON_HEADERS = {"Accept": "application/json"}

def test_create_classroom_success(client, admin_headers):
    payload = {"name": "Room 101", "capacity": 25, "location": "Building A"}
    # Use json=payload instead of data=payload so Flask sends a proper JSON body for Pydantic validation
    response = client.post("/classrooms/create", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data["name"] == "Room 101"
    assert data["capacity"] == 25


def test_create_classroom_missing_required_field(client, admin_headers, app):
    from school_app.extensions import db
    
    with app.app_context():
        before_count = db.session.query(Classroom).count()
    
    payload = {"capacity": 25}  
    # Use json=payload here as well
    response = client.post("/classrooms/create", json=payload, headers=admin_headers)
    
    assert response.status_code == 400


def test_get_classroom_detail_success(client, admin_headers, classroom):
    response = client.get(f"/classrooms/{classroom.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == classroom.id


def test_get_classroom_detail_not_found(client, admin_headers):
    response = client.get("/classrooms/99999", headers=admin_headers)
    assert response.status_code == 404


def test_get_all_classrooms_list(client, admin_headers, classroom):
    response = client.get("/classrooms?list=true", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert any(c["id"] == classroom.id for c in data)


def test_delete_classroom_success(client, admin_headers, classroom):
    response = client.delete(f"/classrooms/{classroom.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Classroom deleted successfully"

    follow_up = client.get(f"/classrooms/{classroom.id}", headers=admin_headers)
    assert follow_up.status_code == 404


def test_delete_classroom_not_found(client, admin_headers):
    response = client.delete("/classrooms/99999", headers=admin_headers)
    assert response.status_code == 404


# ====================================== bulk_assign_students tests ===============================================

def test_bulk_assign_students_success(client, admin_headers, classroom, student, student2):
    payload = {"student_ids": [student.id, student2.id]}
    response = client.post(
        f"/classrooms/{classroom.id}/students/bulk", json=payload, headers=admin_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["classroom_id"] == classroom.id
    assert sorted(data["assigned_ids"]) == sorted([student.id, student2.id])
    assert data["missing_ids"] == []


def test_bulk_assign_students_classroom_not_found(client, admin_headers, student):
    payload = {"student_ids": [student.id]}
    response = client.post(
        "/classrooms/99999/students/bulk", json=payload, headers=admin_headers
    )
    assert response.status_code == 404


def test_bulk_assign_students_with_missing_ids(client, admin_headers, classroom, student):
    payload = {"student_ids": [student.id, 99999]}
    response = client.post(
        f"/classrooms/{classroom.id}/students/bulk", json=payload, headers=admin_headers
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["assigned_ids"] == [student.id]
    assert data["missing_ids"] == [99999]


def test_bulk_assign_students_empty_list_rejected(client, admin_headers, classroom):
    payload = {"student_ids": []}
    response = client.post(
        f"/classrooms/{classroom.id}/students/bulk", json=payload, headers=admin_headers
    )
    assert response.status_code == 400


def test_bulk_assign_students_forbidden_for_non_admin(client, teacher_headers, classroom, student):
    payload = {"student_ids": [student.id]}
    response = client.post(
        f"/classrooms/{classroom.id}/students/bulk", json=payload, headers=teacher_headers
    )
    assert response.status_code == 403