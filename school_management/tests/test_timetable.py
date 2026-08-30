import pytest


def test_create_timetable_success(client, admin_headers, term, classroom, subject, teacher):
    payload = {
        "term_id": term.id,
        "classroom_id": classroom.id,
        "subject_id": subject.id,
        "teacher_id": teacher.id,
        "day_of_week": "MONDAY",
        "start_time": "08:00:00",
        "end_time": "09:00:00",
    }

    response = client.post("/timetables", json=payload, headers=admin_headers)
    data = response.get_json()

    assert response.status_code == 201
    assert data["message"] == "Timetable entry created successfully."


def test_get_timetable_by_id(client, admin_headers, timetable):
    response = client.get(f"/timetables/{timetable.id}", headers=admin_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert data["id"] == timetable.id


def test_get_timetables_paginated(client, admin_headers, timetable):
    response = client.get("/timetables?page=1&per_page=10", headers=admin_headers)
    data = response.get_json()

    assert response.status_code == 200
    assert len(data["items"]) >= 1


def test_update_timetable_success(client, admin_headers, timetable):
    payload = {
        "start_time": "10:00:00",
        "end_time": "11:00:00",
    }

    response = client.put(f"/timetables/{timetable.id}", json=payload, headers=admin_headers)
    data = response.get_json()

    assert response.status_code == 200


def test_delete_timetable_success(client, admin_headers, timetable):
    response = client.delete(f"/timetables/{timetable.id}", headers=admin_headers)
    assert response.status_code == 200


def test_get_teacher_timetable(client, admin_headers, timetable):
    response = client.get(f"/timetables/teacher/{timetable.teacher_id}?term_id={timetable.term_id}", headers=admin_headers)
    assert response.status_code == 200


def test_get_classroom_timetable(client, admin_headers, timetable):
    response = client.get(f"/timetables/classroom/{timetable.classroom_id}?term_id={timetable.term_id}", headers=admin_headers)
    assert response.status_code == 200