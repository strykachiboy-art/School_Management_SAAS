import pytest
from sqlalchemy.exc import OperationalError

from school_app.auth.services.profile import update_profile
from school_app.auth.request.profile import ProfileUpdateRequest
from school_app.extensions import db
from school_app.models.user import User

JSON_HEADERS = {"Accept": "application/json"}


def test_update_profile_success(app, base_user):
    """Test successful update of both username and email."""
    data = ProfileUpdateRequest(username="new_username", email="new@example.com")
    
    with app.app_context():
        # Attach the user to the current session
        db.session.add(base_user) 
        
        updated_user = update_profile(base_user, data)

        assert updated_user.username == "new_username"
        assert updated_user.email == "new@example.com"


def test_update_profile_partial_success(app, base_user):
    """Test updating ONLY the email (username is None)."""
    data = ProfileUpdateRequest(username=None, email="new@example.com")
    old_username = base_user.username

    with app.app_context():
        db.session.add(base_user)
        updated_user = update_profile(base_user, data)

        # Username shouldn't change, email should
        assert updated_user.username == old_username
        assert updated_user.email == "new@example.com"


def test_update_profile_duplicate_username_rolls_back(app, base_user, make_user):
    """Confirms username isn't left mutated in session after a duplicate-username failure."""
    conflict_user = make_user("conflict")
    data = ProfileUpdateRequest(username=conflict_user.username)
    original_username = base_user.username

    with app.app_context():
        db.session.add(base_user)

        with pytest.raises(ValueError, match="Username already exists"):
            update_profile(base_user, data)

        assert base_user.username == original_username
        assert db.session.is_active


def test_update_profile_duplicate_email(app, base_user, make_user):
    """Test updating to an email that already belongs to someone else."""
    conflict_user = make_user("conflict")
    data = ProfileUpdateRequest(username=None, email=conflict_user.email)
    
    with app.app_context():
        db.session.add(base_user)

        with pytest.raises(ValueError, match="Email already exists"):
            update_profile(base_user, data)


def test_update_profile_db_error(app, base_user, monkeypatch):
    """Test that a DB error triggers a rollback and raises a clean RuntimeError."""
    data = ProfileUpdateRequest(username="new_username", email="new@example.com")
    
    # We use monkeypatch to force db.session.commit to throw an OperationalError
    def mock_commit():
        raise OperationalError("Simulated DB connection drop", None, None)

    with app.app_context():
        db.session.add(base_user)
        monkeypatch.setattr(db.session, "commit", mock_commit)

        with pytest.raises(RuntimeError, match="A database error occurred while updating the profile."):
            update_profile(base_user, data)
            
        # Verify the session is still active and clean (rollback occurred)
        assert db.session.is_active