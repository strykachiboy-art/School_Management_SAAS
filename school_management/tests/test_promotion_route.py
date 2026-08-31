import pytest
from school_app.models.student import Student
from school_app.models.promotion_history import PromotionHistory


# ====================================== evaluation tests ===============================================

def test_evaluate_promotion_route_success(json_client, teacher_headers, student, academic_session):
    response = json_client.get(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/evaluate",
        headers=teacher_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["student_id"] == student.id
    assert "recommendation" in data


def test_evaluate_promotion_route_unauthenticated(json_client, student, academic_session):
    response = json_client.get(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/evaluate"
    )
    assert response.status_code in (401, 403)


def test_evaluate_promotion_route_not_found(json_client, teacher_headers, academic_session):
    response = json_client.get(
        f"/promotions/students/9999/sessions/{academic_session.id}/evaluate",
        headers=teacher_headers,
    )
    assert response.status_code == 404


# ====================================== promotion action tests ===============================================

def test_promote_student_route_success(json_client, teacher_headers, student, academic_session, classroom, db_session):
    response = json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/promote",
        json={"to_classroom_id": classroom.id, "allow_level_skip": True},
        headers=teacher_headers,
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["student_id"] == student.id
    assert data["to_classroom_id"] == classroom.id

    # Verify side effect in DB
    updated_student = db_session.get(Student, student.id)
    assert updated_student.classroom_id == classroom.id


def test_promote_student_invalid_target_classroom(json_client, teacher_headers, student, academic_session):
    response = json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/promote",
        json={"to_classroom_id": 9999},
        headers=teacher_headers,
    )
    assert response.status_code == 400


def test_repeat_student_route_admin_success(json_client, admin_headers, student, academic_session):
    response = json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/repeat",
        json={"remarks": "Needs improvement"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["decision"] == "repeated"


def test_repeat_student_route_teacher_forbidden(json_client, teacher_headers, student, academic_session):
    response = json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/repeat",
        json={"remarks": "Needs improvement"},
        headers=teacher_headers,
    )
    assert response.status_code == 403


def test_graduate_student_route_admin_success(json_client, admin_headers, student, academic_session, db_session):
    response = json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/graduate",
        json={"remarks": "Successfully completed final year"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["decision"] == "graduated"

    # Verify student is unassigned from classroom upon graduation
    updated_student = db_session.get(Student, student.id)
    assert updated_student.classroom_id is None


# ====================================== history routes ===============================================

def test_student_promotion_history_route_admin_can_view(json_client, admin_headers, student, academic_session):
    json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/repeat",
        json={"remarks": "First"},
        headers=admin_headers,
    )

    response = json_client.get(f"/promotions/students/{student.id}/history", headers=admin_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) == 1
    assert data["items"][0]["remarks"] == "First"


def test_student_promotion_history_route_invalid_pagination(json_client, admin_headers, student):
    response = json_client.get(
        f"/promotions/students/{student.id}/history?page=invalid",
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_student_promotion_history_route_student_can_view_own(json_client, admin_headers, student_headers, student, academic_session):
    json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/repeat",
        json={},
        headers=admin_headers,
    )

    response = json_client.get(f"/promotions/students/{student.id}/history", headers=student_headers)
    assert response.status_code == 200


def test_student_promotion_history_route_student_cannot_view_others(json_client, student_headers, student2):
    response = json_client.get(f"/promotions/students/{student2.id}/history", headers=student_headers)
    assert response.status_code == 403


def test_session_promotions_route_admin_only(json_client, admin_headers, teacher_headers, student, student2, academic_session, classroom):
    json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/promote",
        json={"to_classroom_id": classroom.id, "allow_level_skip": True},
        headers=teacher_headers,
    )
    json_client.post(
        f"/promotions/students/{student2.id}/sessions/{academic_session.id}/repeat",
        json={},
        headers=admin_headers,
    )

    response = json_client.get(f"/promotions/sessions/{academic_session.id}", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_session_promotions_route_filter_by_decision(json_client, admin_headers, teacher_headers, student, student2, academic_session, classroom):
    json_client.post(
        f"/promotions/students/{student.id}/sessions/{academic_session.id}/promote",
        json={"to_classroom_id": classroom.id, "allow_level_skip": True},
        headers=teacher_headers,
    )
    json_client.post(
        f"/promotions/students/{student2.id}/sessions/{academic_session.id}/repeat",
        json={},
        headers=admin_headers,
    )

    response = json_client.get(
        f"/promotions/sessions/{academic_session.id}?decision=promoted",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["decision"] == "promoted"


def test_session_promotions_route_invalid_decision_param(json_client, admin_headers, academic_session):
    response = json_client.get(
        f"/promotions/sessions/{academic_session.id}?decision=invalid_value",
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_session_promotions_route_forbidden_for_student(json_client, student_headers, academic_session):
    response = json_client.get(f"/promotions/sessions/{academic_session.id}", headers=student_headers)
    assert response.status_code == 403


# ====================================== bulk action tests ===============================================

def test_bulk_promote_session_route_admin_success(json_client, admin_headers, academic_session):
    response = json_client.post(
        f"/promotions/sessions/{academic_session.id}/bulk-promote",
        json={},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "promoted" in data
    assert "repeated" in data


def test_bulk_promote_session_route_teacher_forbidden(json_client, teacher_headers, academic_session):
    response = json_client.post(
        f"/promotions/sessions/{academic_session.id}/bulk-promote",
        json={},
        headers=teacher_headers,
    )
    assert response.status_code == 403