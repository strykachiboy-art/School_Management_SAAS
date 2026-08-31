import pytest
from werkzeug.exceptions import HTTPException
from school_app.models.teacher_permission import TeacherPermission
from school_app.enums.permission import Permission
from school_app.modules.people.services.teacher_permission_service import (
    assign_teacher_permission,
    get_teacher_permissions,
    get_all_teacher_permissions,
    update_teacher_permissions,
    remove_teacher_permission,
)

def test_service_assign_permission_success(app, db_session, sample_teacher):
    """Test service successfully assigns a single permission."""
    with app.app_context():
        record = assign_teacher_permission(sample_teacher.id, Permission.MARK_ATTENDANCE, school_id=sample_teacher.school_id)
        assert record.id is not None
        assert record.teacher_id == sample_teacher.id
        assert record.permission == Permission.MARK_ATTENDANCE


def test_service_assign_permission_duplicate_raises_error(app, db_session, sample_teacher):
    """Test assigning a duplicate permission raises an HTTP 400 exception."""
    with app.app_context():
        assign_teacher_permission(sample_teacher.id, Permission.ENTER_GRADES, school_id=sample_teacher.school_id)

        with pytest.raises(HTTPException) as exc_info:
            assign_teacher_permission(sample_teacher.id, Permission.ENTER_GRADES, school_id=sample_teacher.school_id)
        assert exc_info.value.code == 400


def test_service_get_teacher_permissions(app, db_session, sample_teacher):
    """Test retrieving permissions for a specific teacher."""
    with app.app_context():
        assign_teacher_permission(sample_teacher.id, Permission.VIEW_TIMETABLE, school_id=sample_teacher.school_id)
        permissions = get_teacher_permissions(sample_teacher.id, school_id=sample_teacher.school_id)

        assert len(permissions) == 1
        assert permissions[0].permission == Permission.VIEW_TIMETABLE


def test_service_update_teacher_permissions(app, db_session, sample_teacher):
    """Test replacing a teacher's full permission set."""
    with app.app_context():
        assign_teacher_permission(sample_teacher.id, Permission.VIEW_TIMETABLE, school_id=sample_teacher.school_id)

        updated = update_teacher_permissions(
            sample_teacher.id,
            [Permission.ENTER_GRADES, Permission.UPDATE_GRADES],
            school_id=sample_teacher.school_id
        )

        perms = {r.permission for r in updated}
        assert perms == {Permission.ENTER_GRADES, Permission.UPDATE_GRADES}
        assert Permission.VIEW_TIMETABLE not in perms


def test_service_remove_teacher_permission(app, db_session, sample_teacher):
    """Test removing a specific permission from a teacher."""
    with app.app_context():
        assign_teacher_permission(sample_teacher.id, Permission.MANAGE_TEACHERS, school_id=sample_teacher.school_id)