# test/test_student.py

def test_create_student_success(client, admin_headers, classroom):
    payload = {
        "username": "new_student",
        "full_name": "John Smith",
        "email": "john.smith@example.com",
        "phone": "0987654321",
        "admission_number": "ADM001",
        "classroom_id": str(classroom.id),
        "password": "securepass123",
    }
    # Use json=payload instead of data=payload so Flask sends a proper JSON body 
    # for Pydantic's @validate_request decorator
    response = client.post("/students/create", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.get_json()
    assert data["full_name"] == "John Smith"
    assert data["classroom_id"] == classroom.id


def test_create_student_duplicate_username(client, admin_headers, student):
    """student fixture already created a user with username 'student_1'."""
    payload = {
        "username": "student_1",
        "full_name": "Duplicate",
        "email": "unique_email2@example.com",
        "password": "securepass123",
    }
    response = client.post("/students/create", json=payload, headers=admin_headers)
    assert response.status_code == 400


def test_get_student_success(client, admin_headers, student):
    response = client.get(f"/students/{student.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == student.id


def test_get_student_not_found(client, admin_headers):
    response = client.get("/students/99999", headers=admin_headers)
    assert response.status_code == 404


def test_get_all_students(client, admin_headers, student):
    response = client.get("/students", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert any(s["id"] == student.id for s in data)


def test_filter_students_by_classroom(client, admin_headers, student, classroom):
    response = client.get(f"/students?classroom_id={classroom.id}", headers=admin_headers)
    assert response.status_code == 200


def test_delete_student_success(client, admin_headers, student):
    response = client.delete(f"/students/{student.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["message"] == "Student deleted successfully"


def test_delete_student_not_found(client, admin_headers):
    response = client.delete("/students/99999", headers=admin_headers)
    assert response.status_code == 404
    
    
def test_add_student_to_classroom_success(client, admin_headers, student, classroom):
    response = client.patch(f"/students/{student.id}/classroom/{classroom.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["classroom_id"] == classroom.id


def test_add_student_to_classroom_student_not_found(client, admin_headers, classroom):
    response = client.patch(f"/students/99999/classroom/{classroom.id}", headers=admin_headers)
    assert response.status_code == 404


def test_delete_student_from_classroom_success(client, admin_headers, student, classroom):
    # First assign the student to a classroom so removal has something to undo
    client.patch(f"/students/{student.id}/classroom/{classroom.id}", headers=admin_headers)

    response = client.delete(f"/students/{student.id}/classroom", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["classroom_id"] is None


def test_delete_student_from_classroom_not_found(client, admin_headers):
    response = client.delete("/students/99999/classroom", headers=admin_headers)
    assert response.status_code == 404