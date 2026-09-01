import pytest


# ======================================================================
# Create Timetable
# ======================================================================

def test_create_timetable_success(
    client,
    admin_headers,
    term,
    classroom,
    subject,
    teacher,
):
    payload = {
        "term_id": term.id,
        "classroom_id": classroom.id,
        "subject_id": subject.id,
        "teacher_id": teacher.id,
        "day_of_week": "MONDAY",
        "start_time": "08:00:00",
        "end_time": "09:00:00",
    }

    response = client.post(
        "/timetables",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Timetable entry created successfully."
    assert data["data"]["term_id"] == term.id
    assert data["data"]["classroom_id"] == classroom.id
    assert data["data"]["subject_id"] == subject.id
    assert data["data"]["teacher_id"] == teacher.id
    assert data["data"]["day_of_week"] == "MONDAY"
    assert data["data"]["start_time"] == "08:00:00"
    assert data["data"]["end_time"] == "09:00:00"


def test_create_timetable_invalid_time(
    client,
    admin_headers,
    term,
    classroom,
    subject,
    teacher,
):
    """start_time must be earlier than end_time."""

    payload = {
        "term_id": term.id,
        "classroom_id": classroom.id,
        "subject_id": subject.id,
        "teacher_id": teacher.id,
        "day_of_week": "MONDAY",
        "start_time": "10:00:00",
        "end_time": "09:00:00",
    }

    response = client.post(
        "/timetables",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_create_timetable_invalid_foreign_key(
    client,
    admin_headers,
    term,
    classroom,
    subject,
    teacher,
):
    """A related record that does not exist should be rejected."""

    payload = {
        "term_id": 999999,
        "classroom_id": classroom.id,
        "subject_id": subject.id,
        "teacher_id": teacher.id,
        "day_of_week": "MONDAY",
        "start_time": "08:00:00",
        "end_time": "09:00:00",
    }

    response = client.post(
        "/timetables",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# Get Timetable
# ======================================================================

def test_get_timetable_by_id(
    client,
    admin_headers,
    timetable,
):
    response = client.get(
        f"/timetables/{timetable.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == timetable.id
    assert data["term_id"] == timetable.term_id
    assert data["classroom_id"] == timetable.classroom_id
    assert data["subject_id"] == timetable.subject_id
    assert data["teacher_id"] == timetable.teacher_id


def test_get_timetable_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/timetables/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# Get All Timetables
# ======================================================================

def test_get_timetables_paginated(
    client,
    admin_headers,
    timetable,
):
    response = client.get(
        "/timetables?page=1&per_page=10",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert "items" in data
    assert "total" in data
    assert "pages" in data
    assert "page" in data
    assert "per_page" in data

    assert len(data["items"]) >= 1


def test_get_timetables_by_term(
    client,
    admin_headers,
    timetable,
):
    response = client.get(
        f"/timetables?term_id={timetable.term_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert all(
        item["term_id"] == timetable.term_id
        for item in data["items"]
    )


# ======================================================================
# Update Timetable
# ======================================================================

def test_update_timetable_success(
    client,
    admin_headers,
    timetable,
):
    payload = {
        "start_time": "10:00:00",
        "end_time": "11:00:00",
    }

    response = client.put(
        f"/timetables/{timetable.id}",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Timetable entry updated successfully."
    assert data["data"]["id"] == timetable.id
    assert data["data"]["start_time"] == "10:00:00"
    assert data["data"]["end_time"] == "11:00:00"


def test_update_timetable_invalid_time(
    client,
    admin_headers,
    timetable,
):
    payload = {
        "start_time": "12:00:00",
        "end_time": "11:00:00",
    }

    response = client.put(
        f"/timetables/{timetable.id}",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 400


def test_update_timetable_not_found(
    client,
    admin_headers,
):
    payload = {
        "start_time": "10:00:00",
        "end_time": "11:00:00",
    }

    response = client.put(
        "/timetables/999999",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# Delete Timetable
# ======================================================================

def test_delete_timetable_success(
    client,
    admin_headers,
    timetable,
):
    response = client.delete(
        f"/timetables/{timetable.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Timetable entry deleted successfully."


def test_delete_timetable_not_found(
    client,
    admin_headers,
):
    response = client.delete(
        "/timetables/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# Teacher Timetable
# ======================================================================

def test_get_teacher_timetable(
    client,
    admin_headers,
    timetable,
):
    response = client.get(
        f"/timetables/teacher/{timetable.teacher_id}"
        f"?term_id={timetable.term_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)

    assert all(
        item["teacher_id"] == timetable.teacher_id
        for item in data
    )


def test_get_teacher_timetable_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/timetables/teacher/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ======================================================================
# Classroom Timetable
# ======================================================================

def test_get_classroom_timetable(
    client,
    admin_headers,
    timetable,
):
    response = client.get(
        f"/timetables/classroom/{timetable.classroom_id}"
        f"?term_id={timetable.term_id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)

    assert all(
        item["classroom_id"] == timetable.classroom_id
        for item in data
    )


def test_get_classroom_timetable_not_found(
    client,
    admin_headers,
):
    response = client.get(
        "/timetables/classroom/999999",
        headers=admin_headers,
    )

    assert response.status_code == 404