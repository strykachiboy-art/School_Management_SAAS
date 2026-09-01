import pytest
from werkzeug.exceptions import BadRequest

from school_app.extensions import db
from school_app.models.school import School
from school_app.modules.school.services.school_service import (
    create_school,
    get_all_schools,
    get_school,
    get_school_by_slug,
    update_school,
    delete_school,
)


# ======================================================================
# Helpers
# ======================================================================

class FakeSchoolCreateRequest:
    def __init__(
        self,
        name="Test Academy",
        slug="test-academy",
        country="Nigeria",
        timezone="Africa/Lagos",
        currency="NGN",
        locale="en-NG",
    ):
        self.name = name
        self.slug = slug
        self.country = country
        self.timezone = timezone
        self.currency = currency
        self.locale = locale


class FakeSchoolUpdateRequest:
    def __init__(
        self,
        name=None,
        country=None,
        timezone=None,
        currency=None,
        locale=None,
        is_active=None,
        onboarding_completed=None,
    ):
        self.name = name
        self.country = country
        self.timezone = timezone
        self.currency = currency
        self.locale = locale
        self.is_active = is_active
        self.onboarding_completed = onboarding_completed


# ======================================================================
# Create
# ======================================================================

def test_create_school_success(app, admin_actor_id):
    with app.app_context():
        data = FakeSchoolCreateRequest(
            name="New School",
            slug="new-school",
            country="Nigeria",
            timezone="Africa/Lagos",
            currency="NGN",
            locale="en-NG",
        )

        school = create_school(
            data,
            actor_id=admin_actor_id,
        )

        assert school.id is not None
        assert school.name == "New School"
        assert school.slug == "new-school"
        assert school.country == "Nigeria"
        assert school.timezone == "Africa/Lagos"
        assert school.currency == "NGN"
        assert school.locale == "en-NG"


def test_create_school_duplicate_slug_is_rejected(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        data = FakeSchoolCreateRequest(
            name="Another School",
            slug=school.slug,
        )

        with pytest.raises(BadRequest) as exc_info:
            create_school(
                data,
                actor_id=admin_actor_id,
            )

        assert exc_info.value.code == 400
        assert "slug" in exc_info.value.description.lower()


# ======================================================================
# Get Single
# ======================================================================

def test_get_school_success(app, school):
    with app.app_context():
        result = get_school(school.id)

        assert result is not None
        assert result.id == school.id
        assert result.name == school.name
        assert result.slug == school.slug


def test_get_school_not_found(app):
    with app.app_context():
        result = get_school(999999)

        assert result is None


# ======================================================================
# Get By Slug
# ======================================================================

def test_get_school_by_slug_success(app, school):
    with app.app_context():
        result = get_school_by_slug(school.slug)

        assert result is not None
        assert result.id == school.id
        assert result.slug == school.slug


def test_get_school_by_slug_is_case_insensitive(app, school):
    with app.app_context():
        result = get_school_by_slug(
            school.slug.upper()
        )

        assert result is not None
        assert result.id == school.id


def test_get_school_by_slug_not_found(app):
    with app.app_context():
        result = get_school_by_slug("does-not-exist")

        assert result is None


# ======================================================================
# Get All
# ======================================================================

def test_get_all_schools_returns_active_schools(
    app,
    school,
):
    with app.app_context():
        result = get_all_schools()

        assert result.total >= 1

        assert all(
            item.is_active is True
            for item in result.items
        )


def test_get_all_schools_can_include_inactive(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        school_db = db.session.get(
            School,
            school.id,
        )

        school_db.is_active = False
        db.session.commit()

        result = get_all_schools(
            include_inactive=True,
        )

        assert any(
            item.id == school.id
            for item in result.items
        )


def test_get_all_schools_excludes_inactive_by_default(
    app,
    school,
):
    with app.app_context():
        school_db = db.session.get(
            School,
            school.id,
        )

        school_db.is_active = False
        db.session.commit()

        result = get_all_schools()

        assert all(
            item.id != school.id
            for item in result.items
        )


def test_get_all_schools_search_by_name(
    app,
    school,
):
    with app.app_context():
        result = get_all_schools(
            search="Test School",
        )

        assert any(
            item.id == school.id
            for item in result.items
        )


def test_get_all_schools_search_no_match(app):
    with app.app_context():
        result = get_all_schools(
            search="Definitely Does Not Exist",
        )

        assert result.total == 0
        assert result.items == []


def test_get_all_schools_pagination(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        for index in range(3):
            data = FakeSchoolCreateRequest(
                name=f"School {index}",
                slug=f"school-{index}",
            )

            create_school(
                data,
                actor_id=admin_actor_id,
            )

        result = get_all_schools(
            page=1,
            per_page=2,
        )

        assert result.page == 1
        assert result.per_page == 2
        assert len(result.items) <= 2
        assert result.total >= 4


# ======================================================================
# Update
# ======================================================================

def test_update_school_success(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        data = FakeSchoolUpdateRequest(
            name="Updated School",
            country="Ghana",
            timezone="Africa/Accra",
            currency="GHS",
            locale="en-GH",
            is_active=False,
            onboarding_completed=True,
        )

        updated = update_school(
            data,
            school.id,
            actor_id=admin_actor_id,
        )

        assert updated is not None
        assert updated.id == school.id
        assert updated.name == "Updated School"
        assert updated.country == "Ghana"
        assert updated.timezone == "Africa/Accra"
        assert updated.currency == "GHS"
        assert updated.locale == "en-GH"
        assert updated.is_active is False
        assert updated.onboarding_completed is True


def test_update_school_partial_update(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        original_country = school.country

        data = FakeSchoolUpdateRequest(
            name="Partially Updated School",
        )

        updated = update_school(
            data,
            school.id,
            actor_id=admin_actor_id,
        )

        assert updated.name == "Partially Updated School"
        assert updated.country == original_country


def test_update_school_not_found(
    app,
    admin_actor_id,
):
    with app.app_context():
        data = FakeSchoolUpdateRequest(
            name="Does Not Exist",
        )

        result = update_school(
            data,
            999999,
            actor_id=admin_actor_id,
        )

        assert result is None


# ======================================================================
# Delete
# ======================================================================

def test_delete_school_success(
    app,
    admin_actor_id,
):
    with app.app_context():
        school = School(
            name="Delete Me School",
            slug="delete-me-school",
        )

        db.session.add(school)
        db.session.commit()

        school_id = school.id

        result = delete_school(
            school_id,
            actor_id=admin_actor_id,
        )

        assert result is True

        deleted = db.session.get(
            School,
            school_id,
        )

        assert deleted is None


def test_delete_school_not_found(
    app,
    admin_actor_id,
):
    with app.app_context():
        result = delete_school(
            999999,
            actor_id=admin_actor_id,
        )

        assert result is False


def test_delete_school_with_users_is_rejected(
    app,
    school,
    make_user,
    admin_actor_id,
):
    with app.app_context():
        user = make_user(
            suffix="school_delete",
            role="student",
        )

        assert user.school_id == school.id

        with pytest.raises(BadRequest) as exc_info:
            delete_school(
                school.id,
                actor_id=admin_actor_id,
            )

        assert exc_info.value.code == 400
        assert "Cannot delete school" in exc_info.value.description
        assert "user(s) attached" in exc_info.value.description


# ======================================================================
# School isolation / user relationship
# ======================================================================

def test_delete_school_allows_school_without_users(
    app,
    admin_actor_id,
):
    with app.app_context():
        school = School(
            name="Empty School",
            slug="empty-school",
        )

        db.session.add(school)
        db.session.commit()

        result = delete_school(
            school.id,
            actor_id=admin_actor_id,
        )

        assert result is True
