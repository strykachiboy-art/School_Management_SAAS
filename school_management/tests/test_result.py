from school_app.extensions import db as _db
from school_app.models.result import Result

JSON_HEADERS = {"Accept": "application/json"}


# ======================================================================
# Create Result
# ======================================================================

def test_create_result_success(client, admin_headers, student, exam, school):
    payload = {
        "student_id": student.id,
        "exam_id": exam.id,
        "marks_obtained": 92.5,
    }
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }

    response = client.post(
        "/results/create",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["marks_obtained"] == 92.5
    assert data["student_id"] == student.id
    assert data["exam_id"] == exam.id

    # Verify the result was actually persisted with the correct tenant.
    with client.application.app_context():
        created_result = _db.session.get(
            Result,
            data["id"],
        )

        assert created_result is not None
        assert created_result.school_id == school.id
        assert created_result.student_id == student.id
        assert created_result.exam_id == exam.id
        assert created_result.marks_obtained == 92.5


def test_create_result_validation_error(client, admin_headers):
    payload = {
        "exam_id": 1,
    }
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }

    response = client.post(
        "/results/create",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 400


def test_create_result_negative_marks_rejected(
    client,
    admin_headers,
    student,
    exam,
):
    payload = {
        "student_id": student.id,
        "exam_id": exam.id,
        "marks_obtained": -5,
    }
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }

    response = client.post(
        "/results/create",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 400


def test_create_result_student_not_found(
    client,
    admin_headers,
    exam,
):
    payload = {
        "student_id": 99999,
        "exam_id": exam.id,
        "marks_obtained": 92.5,
    }
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }

    response = client.post(
        "/results/create",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 404


def test_create_result_exam_not_found(
    client,
    admin_headers,
    student,
):
    payload = {
        "student_id": student.id,
        "exam_id": 99999,
        "marks_obtained": 92.5,
    }
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }

    response = client.post(
        "/results/create",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 404


# ======================================================================
# Get Results
# ======================================================================

def test_get_all_results(client, admin_headers, result):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        "/results/",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_result_by_id(client, admin_headers, result):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        f"/results/{result.id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == result.id
    assert data["student_id"] == result.student_id
    assert data["exam_id"] == result.exam_id
    assert data["marks_obtained"] == result.marks_obtained


def test_get_result_not_found(client, admin_headers):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        "/results/9999",
        headers=headers,
    )

    assert response.status_code == 404


# ======================================================================
# Delete Result
# ======================================================================

def test_delete_result(client, admin_headers, result):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.delete(
        f"/results/{result.id}/delete",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Result deleted successfully"

    # Verify it is actually deleted.
    check_response = client.get(
        f"/results/{result.id}",
        headers=headers,
    )

    assert check_response.status_code == 404


# ======================================================================
# Search Result
# ======================================================================

def test_search_results_by_student(
    client,
    admin_headers,
    result,
    student,
):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        f"/results/search?student_id={student.id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(item["student_id"] == student.id for item in data)


def test_search_results_by_exam(
    client,
    admin_headers,
    result,
    exam,
):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        f"/results/search?exam_id={exam.id}",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(item["exam_id"] == exam.id for item in data)


def test_search_results_without_filters(
    client,
    admin_headers,
    result,
):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        "/results/search",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) >= 1


# ======================================================================
# Pagination
# ======================================================================

def test_search_results_pagination(
    client,
    admin_headers,
    result,
):
    headers = {
        **admin_headers,
        **JSON_HEADERS,
    }
    response = client.get(
        "/results/search?paginate=true",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert "items" in data
    assert "page" in data
    assert "pages" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1