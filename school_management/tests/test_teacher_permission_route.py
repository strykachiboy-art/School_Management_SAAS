import pytest
from sqlalchemy import select

from school_app.enums.permission import Permission
from school_app.models.teacher_permission import TeacherPermission

JSON_HEADERS = {"Accept": "application/json"}


# ======================================================================
# Teacher Permission Route Tests
# ======================================================================

def test_route_assign_permission_success(client, admin_headers, sample_teacher):
    """Test POST /admin/teachers/<id>/permissions."""
    payload = {"permission": "mark_attendance"}

    response = client.post(
        f"/admin/teachers/{sample_teacher.id}/permissions",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data["message"] == "Permission assigned successfully."
    assert data["data"]["teacher_id"] == sample_teacher.id
    assert data["data"]["permission"] == "mark_attendance"


def test_route_get_teacher_permissions_success(
    client,
    admin_headers,
    sample_teacher,
    db_session,
):
    """Test GET /admin/teachers/<id>/permissions."""
    db_session.add(
        TeacherPermission(
            school_id=sample_teacher.school_id,
            teacher_id=sample_teacher.id,
            permission=Permission.ENTER_GRADES,
        )
    )
    db_session.commit()

    response = client.get(
        f"/admin/teachers/{sample_teacher.id}/permissions",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["teacher_id"] == sample_teacher.id
    assert data[0]["permission"] == "enter_grades"


def test_route_update_permissions_success(
    client,
    admin_headers,
    sample_teacher,
):
    """Test PUT /admin/teachers/<id>/permissions."""
    payload = {
        "permissions": [
            "enter_grades",
            "update_grades",
        ]
    }

    response = client.put(
        f"/admin/teachers/{sample_teacher.id}/permissions",
        json=payload,
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Permissions updated successfully."

    returned_permissions = {
        item["permission"]
        for item in data["data"]
    }

    assert returned_permissions == {
        "enter_grades",
        "update_grades",
    }

    assert all(
        item["teacher_id"] == sample_teacher.id
        for item in data["data"]
    )


def test_route_remove_permission_success(
    client,
    admin_headers,
    sample_teacher,
    db_session,
):
    """Test DELETE /admin/teachers/<id>/permissions/<permission_value>."""
    record = TeacherPermission(
        school_id=sample_teacher.school_id,
        teacher_id=sample_teacher.id,
        permission=Permission.MANAGE_TEACHERS,
    )

    db_session.add(record)
    db_session.commit()

    response = client.delete(
        f"/admin/teachers/{sample_teacher.id}/permissions/manage_teachers",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["message"] == "Permission removed successfully."

    remaining = db_session.scalar(
        select(TeacherPermission).where(
            TeacherPermission.school_id == sample_teacher.school_id,
            TeacherPermission.teacher_id == sample_teacher.id,
            TeacherPermission.permission == Permission.MANAGE_TEACHERS,
        )
    )

    assert remaining is None


def test_route_remove_permission_invalid_value(
    client,
    admin_headers,
    sample_teacher,
):
    """Test DELETE with an invalid permission value."""
    response = client.delete(
        f"/admin/teachers/{sample_teacher.id}/permissions/not_a_real_permission",
        headers=admin_headers,
    )

    assert response.status_code == 400

    data = response.get_json()

    # The exact error key depends on your application's error handler.
    # This supports the common "error" and "detail" formats.
    error_message = data.get("message") or data.get("error") or data.get("detail")

    assert error_message is not None
    assert "not_a_real_permission" in error_message


def test_route_get_all_permissions_success(
    client,
    admin_headers,
    sample_teacher,
    db_session,
):
    """Test GET /admin/teachers/permissions."""
    db_session.add(
        TeacherPermission(
            school_id=sample_teacher.school_id,
            teacher_id=sample_teacher.id,
            permission=Permission.VIEW_RESULTS,
        )
    )

    db_session.commit()

    response = client.get(
        "/admin/teachers/permissions",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.get_json()

    assert isinstance(data, list)

    matching = [
        item
        for item in data
        if item["teacher_id"] == sample_teacher.id
        and item["permission"] == "view_results"
    ]

    assert len(matching) == 1