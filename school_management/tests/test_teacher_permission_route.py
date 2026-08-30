from school_app.models.teacher_permission import TeacherPermission
from school_app.enums.permission import Permission

def test_route_assign_permission_success(client, admin_headers, sample_teacher):
    """Test POST /admin/teachers/<id>/permissions"""
    payload = {"permission": "mark_attendance"}
    response = client.post(
        f"/admin/teachers/{sample_teacher.id}/permissions", 
        json=payload, 
        headers=admin_headers
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data["message"] == "Permission assigned successfully."
    assert data["data"]["permission"] == "mark_attendance"


def test_route_get_teacher_permissions_success(client, admin_headers, sample_teacher, db_session):
    """Test GET /admin/teachers/<id>/permissions"""
    db_session.add(TeacherPermission(teacher_id=sample_teacher.id, permission=Permission.ENTER_GRADES))
    db_session.commit()

    response = client.get(
        f"/admin/teachers/{sample_teacher.id}/permissions", 
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["permission"] == "enter_grades"


def test_route_update_permissions_success(client, admin_headers, sample_teacher):
    """Test PUT /admin/teachers/<id>/permissions"""
    payload = {"permissions": ["enter_grades", "update_grades"]}
    response = client.put(
        f"/admin/teachers/{sample_teacher.id}/permissions", 
        json=payload, 
        headers=admin_headers
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Permissions updated successfully."
    assert len(data["data"]) == 2


def test_route_remove_permission_success(client, admin_headers, sample_teacher, db_session):
    """Test DELETE /admin/teachers/<id>/permissions/<permission_value>"""
    db_session.add(TeacherPermission(teacher_id=sample_teacher.id, permission=Permission.MANAGE_TEACHERS))
    db_session.commit()

    response = client.delete(
        f"/admin/teachers/{sample_teacher.id}/permissions/manage_teachers", 
        headers=admin_headers
    )

    assert response.status_code == 200
    assert response.get_json()["message"] == "Permission removed successfully."


def test_route_remove_permission_invalid_value(client, admin_headers, sample_teacher):
    """Test DELETE with an invalid permission enum string returns 400"""
    response = client.delete(
        f"/admin/teachers/{sample_teacher.id}/permissions/invalid_perm", 
        headers=admin_headers
    )

    assert response.status_code == 400
    assert "is not a valid permission" in response.get_json()["error"].lower()


def test_route_get_all_permissions_success(client, admin_headers, sample_teacher, db_session):
    """Test GET /admin/teachers/permissions"""
    db_session.add(TeacherPermission(teacher_id=sample_teacher.id, permission=Permission.VIEW_RESULTS))
    db_session.commit()

    response = client.get("/admin/teachers/permissions", headers=admin_headers)

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1