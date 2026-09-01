from datetime import date
from school_app.enums.attendance import AttendanceStatus


# ============================ 1. Test Create Attendance ============================

def test_create_attendance_success(json_client, admin_headers, student, term):
    payload = {
        "student_id": student.id,
        "term_id": term.id,
        "date": date.today().isoformat(),
        "status": AttendanceStatus.PRESENT.value,
    }

    response = json_client.post(
        "/attendances",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 201

    data = response.get_json()
    assert data["student_id"] == student.id
    assert data["term_id"] == term.id
    assert data["status"] == AttendanceStatus.PRESENT.value


def test_create_attendance_invalid_payload(json_client, admin_headers):
    payload = {
        "student_id": "not-an-id",
        "status": "INVALID_STATUS",
    }

    response = json_client.post(
        "/attendances",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 422


# ============================ 2. Test Bulk Mark Attendance ============================

def test_mark_classroom_attendance_success(
    json_client,
    teacher_headers,
    classroom,
    student_in_teacher_classroom,
    term,
):
    payload = {
        "term_id": term.id,
        "date": date.today().isoformat(),
        "attendance_data": [
            {
                "student_id": student_in_teacher_classroom.id,
                "status": AttendanceStatus.PRESENT.value,
            }
        ],
    }

    response = json_client.post(
        f"/attendances/classrooms/{classroom.id}/mark",
        json=payload,
        headers=teacher_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == (
        "Classroom attendance marked successfully."
    )


# ============================ 3. Test Get Attendance By ID ============================

def test_get_attendance_by_id_success(
    json_client,
    admin_headers,
    attendance_record,
):
    response = json_client.get(
        f"/attendances/{attendance_record.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["id"] == attendance_record.id


def test_get_attendance_by_id_not_found(json_client, admin_headers):
    response = json_client.get(
        "/attendances/99999",
        headers=admin_headers,
    )

    assert response.status_code == 404


# ============================ 4. Test Get Student Attendance ============================

def test_get_student_attendance(
    json_client,
    admin_headers,
    student,
    attendance_record,
):
    response = json_client.get(
        f"/attendances/students/{student.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1


# ============================ 5. Test Get Classroom Attendance ============================

def test_get_classroom_attendance(
    json_client,
    admin_headers,
    classroom,
    attendance_record,
):
    response = json_client.get(
        f"/attendances/classrooms/{classroom.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


# ============================ 6. Test Update Attendance ============================

def test_update_attendance_success(
    json_client,
    admin_headers,
    attendance_record,
):
    payload = {
        "status": AttendanceStatus.ABSENT.value,
    }

    response = json_client.patch(
        f"/attendances/{attendance_record.id}",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == AttendanceStatus.ABSENT.value


# ============================ 7. Test Delete Attendance ============================

def test_delete_attendance_success(
    json_client,
    admin_headers,
    attendance_record,
):
    response = json_client.delete(
        f"/attendances/{attendance_record.id}",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert "deleted successfully" in response.get_json()["message"]


# ============================ 8. Test Attendance Summary ============================

def test_get_attendance_summary(
    json_client,
    admin_headers,
    student,
    attendance_record,
):
    response = json_client.get(
        f"/attendances/students/{student.id}/summary",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()
    assert "total_school_days" in data
    assert "attendance_percentage" in data