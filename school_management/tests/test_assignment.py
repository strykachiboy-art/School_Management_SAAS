# tests/test_assignment.py

import pytest

from school_app.extensions import db
from school_app.models.association import (
    teacher_subjects,
    student_subjects,
    classroom_subjects,
)

JSON_HEADERS = {"Accept": "application/json"}


# ============================== Teacher assignment ==============================

def test_assign_subject_to_teachers_success(
    client,
    admin_headers,
    subject,
    teacher,
    school,
    db_session,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject assigned to teachers successfully"

    # Verify the association was created with the required school_id.
    row = db_session.execute(
        db.select(teacher_subjects).where(
            teacher_subjects.c.teacher_id == teacher.id,
            teacher_subjects.c.subject_id == subject.id,
        )
    ).mappings().one()

    assert row["school_id"] == school.id


def test_assign_subject_to_teachers_already_assigned(
    client,
    admin_headers,
    subject,
    teacher,
):
    first_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert first_response.status_code == 200

    # Second attempt should fail because the relationship already exists.
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert response.status_code == 400

    res_data = response.get_json()
    error_msg = (
        res_data.get("error")
        or res_data.get("description")
        or str(res_data)
    )

    assert "already assigned" in error_msg.lower()


def test_assign_subject_to_teachers_subject_not_found(
    client,
    admin_headers,
    teacher,
):
    response = client.post(
        "/assignments/subjects/99999/assign/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_assign_subject_to_teachers_teacher_not_found(
    client,
    admin_headers,
    subject,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": [99999]},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_assign_subject_to_teachers_empty_ids(
    client,
    admin_headers,
    subject,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": []},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_remove_subject_from_teachers_success(
    client,
    admin_headers,
    subject,
    teacher,
):
    assign_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert assign_response.status_code == 200

    response = client.delete(
        f"/assignments/subjects/{subject.id}/remove/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject removed from teachers successfully"


def test_get_teacher_subjects_success(
    client,
    admin_headers,
    subject,
    teacher,
):
    assign_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/teachers",
        json={"teacher_ids": [teacher.id]},
        headers=admin_headers,
    )

    assert assign_response.status_code == 200

    response = client.get(
        f"/assignments/teachers/{teacher.id}/subjects",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["id"] == subject.id


def test_get_teacher_subjects_teacher_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/assignments/teachers/99999/subjects",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ============================== Student assignment ==============================

def test_assign_subject_to_students_success(
    client,
    admin_headers,
    subject,
    student,
    school,
    db_session,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/students",
        json={"student_ids": [student.id]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject assigned to students successfully"

    # Verify required school_id.
    row = db_session.execute(
        db.select(student_subjects).where(
            student_subjects.c.student_id == student.id,
            student_subjects.c.subject_id == subject.id,
        )
    ).mappings().one()

    assert row["school_id"] == school.id


def test_assign_subject_to_students_student_not_found(
    client,
    admin_headers,
    subject,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/students",
        json={"student_ids": [99999]},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_remove_subject_from_students_success(
    client,
    admin_headers,
    subject,
    student,
):
    assign_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/students",
        json={"student_ids": [student.id]},
        headers=admin_headers,
    )

    assert assign_response.status_code == 200

    response = client.delete(
        f"/assignments/subjects/{subject.id}/remove/students",
        json={"student_ids": [student.id]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject removed from students successfully"


def test_get_student_subjects_success(
    client,
    admin_headers,
    subject,
    student,
):
    assign_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/students",
        json={"student_ids": [student.id]},
        headers=admin_headers,
    )

    assert assign_response.status_code == 200

    response = client.get(
        f"/assignments/students/{student.id}/subjects",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["id"] == subject.id


def test_get_student_subjects_student_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/assignments/students/99999/subjects",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ============================== Classroom assignment ==============================

def test_assign_subject_to_classrooms_success(
    client,
    admin_headers,
    subject,
    classroom,
    school,
    db_session,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/classrooms",
        json={"classroom_ids": [classroom.id]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject assigned to classrooms successfully"

    # Verify required school_id.
    row = db_session.execute(
        db.select(classroom_subjects).where(
            classroom_subjects.c.classroom_id == classroom.id,
            classroom_subjects.c.subject_id == subject.id,
        )
    ).mappings().one()

    assert row["school_id"] == school.id


def test_assign_subject_to_classrooms_classroom_not_found(
    client,
    admin_headers,
    subject,
):
    response = client.post(
        f"/assignments/subjects/{subject.id}/assign/classrooms",
        json={"classroom_ids": [99999]},
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_remove_subject_from_classrooms_success(
    client,
    admin_headers,
    subject,
    classroom,
):
    assign_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/classrooms",
        json={"classroom_ids": [classroom.id]},
        headers=admin_headers,
    )

    assert assign_response.status_code == 200

    response = client.delete(
        f"/assignments/subjects/{subject.id}/remove/classrooms",
        json={"classroom_ids": [classroom.id]},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Subject removed from classrooms successfully"


def test_get_classroom_subjects_success(
    client,
    admin_headers,
    subject,
    classroom,
):
    assign_response = client.post(
        f"/assignments/subjects/{subject.id}/assign/classrooms",
        json={"classroom_ids": [classroom.id]},
        headers=admin_headers,
    )

    assert assign_response.status_code == 200

    response = client.get(
        f"/assignments/classrooms/{classroom.id}/subjects",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert len(data) == 1
    assert data[0]["id"] == subject.id


def test_get_classroom_subjects_classroom_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/assignments/classrooms/99999/subjects",
        headers=admin_headers,
    )

    assert response.status_code == 404