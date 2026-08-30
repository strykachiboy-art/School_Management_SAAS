import pytest
from unittest.mock import patch, MagicMock
from school_app.modules.people.services.parent_guardian_service import (
    create_parent_guardian,
    get_parent_guardian,
    get_all_parent_guardians,
    update_parent_guardian,
    delete_parent_guardian,
    assign_student_to_guardian,
    get_guardian_students,
    get_student_guardians,
    update_guardian_student_relationship,
    remove_student_from_guardian
)

# ==========================================
# Parent Guardian Service Tests
# ==========================================

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_create_parent_guardian(mock_db):
    data = {
        "user_id": 1,
        "occupation": "Teacher",
        "email": "teacher@example.com",
        "phone": "1234567890",
        "address": "123 Main St"
    }
    
    result = create_parent_guardian(data)
    
    assert result.user_id == 1
    assert result.occupation == "Teacher"
    mock_db.session.add.assert_called_once()
    mock_db.session.commit.assert_called_once()

from school_app.models.parent_guardian import ParentGuardian

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_get_parent_guardian(mock_db):
    mock_guardian = MagicMock()
    mock_db.session.get.return_value = mock_guardian
    
    result = get_parent_guardian(1)
    
    # Assert it called db.session.get with the real ParentGuardian model
    mock_db.session.get.assert_called_once_with(ParentGuardian, 1)
    assert result == mock_guardian

@patch("school_app.modules.people.services.parent_guardian_service.ParentGuardian")
def test_get_all_parent_guardians(mock_model):
    mock_model.query.all.return_value = ["guardian_1", "guardian_2"]
    
    result = get_all_parent_guardians()
    
    assert len(result) == 2
    assert result == ["guardian_1", "guardian_2"]

@patch("school_app.modules.people.services.parent_guardian_service.db")
@patch("school_app.modules.people.services.parent_guardian_service.get_parent_guardian")
def test_update_parent_guardian_success(mock_get, mock_db):
    mock_guardian = MagicMock()
    mock_get.return_value = mock_guardian
    data = {"occupation": "Engineer"}
    
    result = update_parent_guardian(1, data)
    
    assert result == mock_guardian
    assert mock_guardian.occupation == "Engineer"
    mock_db.session.commit.assert_called_once()

@patch("school_app.modules.people.services.parent_guardian_service.get_parent_guardian")
def test_update_parent_guardian_not_found(mock_get):
    mock_get.return_value = None
    
    result = update_parent_guardian(99, {"occupation": "Engineer"})
    
    assert result is None

@patch("school_app.modules.people.services.parent_guardian_service.db")
@patch("school_app.modules.people.services.parent_guardian_service.get_parent_guardian")
def test_delete_parent_guardian_success(mock_get, mock_db):
    mock_guardian = MagicMock()
    mock_get.return_value = mock_guardian
    
    result = delete_parent_guardian(1)
    
    assert result is True
    mock_db.session.delete.assert_called_once_with(mock_guardian)
    mock_db.session.commit.assert_called_once()

@patch("school_app.modules.people.services.parent_guardian_service.get_parent_guardian")
def test_delete_parent_guardian_not_found(mock_get):
    mock_get.return_value = None
    
    result = delete_parent_guardian(99)
    
    assert result is False


# ==========================================
# Parent Guardian Student Service Tests
# ==========================================

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_assign_student_to_guardian(mock_db):
    data = {
        "parent_guardian_id": 1,
        "student_id": 5,
        "relationship": "MOTHER"
    }
    
    result = assign_student_to_guardian(data)
    
    assert result.parent_guardian_id == 1
    assert result.student_id == 5
    assert result.relationship == "MOTHER"
    mock_db.session.add.assert_called_once()
    mock_db.session.commit.assert_called_once()

@patch("school_app.modules.people.services.parent_guardian_service.ParentGuardianStudent")
def test_get_guardian_students(mock_model):
    mock_model.query.filter_by.return_value.all.return_value = ["student_1", "student_2"]
    
    result = get_guardian_students(1)
    
    mock_model.query.filter_by.assert_called_once_with(parent_guardian_id=1)
    assert result == ["student_1", "student_2"]

@patch("school_app.modules.people.services.parent_guardian_service.ParentGuardianStudent")
def test_get_student_guardians(mock_model):
    mock_model.query.filter_by.return_value.all.return_value = ["guardian_1"]
    
    result = get_student_guardians(5)
    
    mock_model.query.filter_by.assert_called_once_with(student_id=5)
    assert result == ["guardian_1"]

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_update_guardian_student_relationship_success(mock_db):
    mock_assignment = MagicMock()
    mock_db.session.get.return_value = mock_assignment
    data = {"relationship": "FATHER"}
    
    result = update_guardian_student_relationship(1, data)
    
    assert result == mock_assignment
    assert mock_assignment.relationship == "FATHER"
    mock_db.session.commit.assert_called_once()

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_update_guardian_student_relationship_not_found(mock_db):
    mock_db.session.get.return_value = None
    
    result = update_guardian_student_relationship(99, {"relationship": "FATHER"})
    
    assert result is None

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_remove_student_from_guardian_success(mock_db):
    mock_assignment = MagicMock()
    mock_db.session.get.return_value = mock_assignment
    
    result = remove_student_from_guardian(1)
    
    assert result is True
    mock_db.session.delete.assert_called_once_with(mock_assignment)
    mock_db.session.commit.assert_called_once()

@patch("school_app.modules.people.services.parent_guardian_service.db")
def test_remove_student_from_guardian_not_found(mock_db):
    mock_db.session.get.return_value = None
    
    result = remove_student_from_guardian(99)
    
    assert result is False