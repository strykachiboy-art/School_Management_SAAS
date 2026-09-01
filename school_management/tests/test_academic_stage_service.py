# tests/test_academic_stage_service.py

import pytest
from werkzeug.exceptions import BadRequest

from school_app.extensions import db
from school_app.models.academic_stage import AcademicStage
from school_app.modules.academics.services.academic_stage_service import (
    create_academic_stage,
    get_all_academic_stages,
    get_academic_stage,
    update_academic_stage,
    delete_academic_stage,
)


class Data:
    """Simple object used to simulate service input data."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


# ======================================================================
# CREATE
# ======================================================================

def test_create_academic_stage(app, school, admin_actor_id):
    with app.app_context():
        data = Data(
            name=" Primary School ",
            display_order=1,
            is_active=True,
            school_id=school.id,
        )

        stage = create_academic_stage(data, admin_actor_id)

        assert stage.id is not None
        assert stage.name == "Primary School"
        assert stage.display_order == 1
        assert stage.is_active is True
        assert stage.school_id == school.id


def test_create_academic_stage_derives_school_from_actor(app, school, admin_actor_id):
    with app.app_context():
        data = Data(
            name="Secondary School",
            display_order=2,
            is_active=True,
        )

        stage = create_academic_stage(data, admin_actor_id)

        assert stage.id is not None
        assert stage.school_id == school.id
        assert stage.name == "Secondary School"


def test_create_academic_stage_requires_name(app, admin_actor_id):
    with app.app_context():
        data = Data(
            display_order=1,
            is_active=True,
        )

        with pytest.raises(BadRequest) as exc:
            create_academic_stage(data, admin_actor_id)

        assert exc.value.description == "Missing required field: name"


def test_create_academic_stage_requires_school(app, make_user):
    with app.app_context():
        user = make_user(
            suffix="no_school",
            role="admin",
            school_id=None,
        )

        data = Data(
            name="Primary School",
        )

        with pytest.raises(BadRequest) as exc:
            create_academic_stage(data, user.id)

        assert exc.value.description == "Missing required field: school_id"


def test_create_academic_stage_normalizes_name(app, school, admin_actor_id):
    with app.app_context():
        data = Data(
            name=" Nursery School ",
            display_order=1,
            is_active=True,
            school_id=school.id,
        )

        stage = create_academic_stage(data, admin_actor_id)

        assert stage.name == "Nursery School"


def test_create_academic_stage_accepts_num_code(app, school, admin_actor_id):
    with app.app_context():
        data = Data(
            name="Basic School",
            num_code=101,
            display_order=1,
            is_active=True,
            school_id=school.id,
        )

        stage = create_academic_stage(data, admin_actor_id)

        assert stage.id is not None
        assert stage.name == "Basic School"


# ======================================================================
# GET
# ======================================================================

def test_get_academic_stage(app, admin_stage):
    with app.app_context():
        stage = get_academic_stage(admin_stage.id)

        assert stage is not None
        assert stage.id == admin_stage.id
        assert stage.name == admin_stage.name
        assert stage.school_id == admin_stage.school_id


def test_get_academic_stage_returns_none_for_missing_stage(app):
    with app.app_context():
        stage = get_academic_stage(999999)

        assert stage is None


def test_get_all_academic_stages_active_only_by_default(app, school, admin_stage):
    with app.app_context():
        inactive = AcademicStage(
            name="Inactive Stage",
            display_order=2,
            is_active=False,
            school_id=school.id,
        )

        db.session.add(inactive)
        db.session.commit()

        result = get_all_academic_stages()

        names = [stage.name for stage in result.items]

        assert admin_stage.name in names
        assert "Inactive Stage" not in names


def test_get_all_academic_stages_include_inactive(app, school, admin_stage):
    with app.app_context():
        inactive = AcademicStage(
            name="Inactive Stage",
            display_order=2,
            is_active=False,
            school_id=school.id,
        )

        db.session.add(inactive)
        db.session.commit()

        result = get_all_academic_stages(include_inactive=True)

        names = [stage.name for stage in result.items]

        assert admin_stage.name in names
        assert "Inactive Stage" in names


def test_get_all_academic_stages_search(app, school):
    with app.app_context():
        primary = AcademicStage(
            name="Primary School",
            display_order=1,
            is_active=True,
            school_id=school.id,
        )

        secondary = AcademicStage(
            name="Secondary School",
            display_order=2,
            is_active=True,
            school_id=school.id,
        )

        db.session.add_all([primary, secondary])
        db.session.commit()

        result = get_all_academic_stages(search="primary")

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].name == "Primary School"


def test_get_all_academic_stages_search_case_insensitive(app, school):
    with app.app_context():
        stage = AcademicStage(
            name="Primary School",
            display_order=1,
            is_active=True,
            school_id=school.id,
        )

        db.session.add(stage)
        db.session.commit()

        result = get_all_academic_stages(search="PRIMARY")

        assert result.total == 1
        assert result.items[0].name == "Primary School"


def test_get_all_academic_stages_orders_by_display_order(app, school):
    with app.app_context():
        stage_two = AcademicStage(
            name="Secondary School",
            display_order=2,
            is_active=True,
            school_id=school.id,
        )

        stage_one = AcademicStage(
            name="Primary School",
            display_order=1,
            is_active=True,
            school_id=school.id,
        )

        db.session.add_all([stage_two, stage_one])
        db.session.commit()

        result = get_all_academic_stages()

        assert result.items[0].name == "Primary School"
        assert result.items[1].name == "Secondary School"


def test_get_all_academic_stages_pagination(app, school):
    with app.app_context():
        stages = [
            AcademicStage(
                name=f"Stage {i}",
                display_order=i,
                is_active=True,
                school_id=school.id,
            )
            for i in range(1, 6)
        ]

        db.session.add_all(stages)
        db.session.commit()

        result = get_all_academic_stages(page=1, per_page=2)

        assert result.page == 1
        assert result.per_page == 2
        assert result.total == 5
        assert len(result.items) == 2


# ======================================================================
# UPDATE
# ======================================================================

def test_update_academic_stage_name(app, admin_stage, admin_actor_id):
    with app.app_context():
        data = Data(name="Updated Stage")

        updated = update_academic_stage(data, admin_stage.id, admin_actor_id)

        assert updated is not None
        assert updated.id == admin_stage.id
        assert updated.name == "Updated Stage"


def test_update_academic_stage_normalizes_name(app, admin_stage, admin_actor_id):
    with app.app_context():
        data = Data(name=" Updated Stage ")

        updated = update_academic_stage(data, admin_stage.id, admin_actor_id)

        assert updated.name == "Updated Stage"


def test_update_academic_stage_display_order(app, admin_stage, admin_actor_id):
    with app.app_context():
        data = Data(display_order=10)

        updated = update_academic_stage(data, admin_stage.id, admin_actor_id)

        assert updated.display_order == 10


def test_update_academic_stage_active_status(app, admin_stage, admin_actor_id):
    with app.app_context():
        data = Data(is_active=False)

        updated = update_academic_stage(data, admin_stage.id, admin_actor_id)

        assert updated.is_active is False


def test_update_academic_stage_multiple_fields(app, admin_stage, admin_actor_id):
    with app.app_context():
        data = Data(name="Updated Stage", display_order=20, is_active=False)

        updated = update_academic_stage(data, admin_stage.id, admin_actor_id)

        assert updated.name == "Updated Stage"
        assert updated.display_order == 20
        assert updated.is_active is False


def test_update_academic_stage_returns_none_when_missing(app, admin_actor_id):
    with app.app_context():
        data = Data(name="Updated Stage")

        result = update_academic_stage(data, 999999, admin_actor_id)

        assert result is None


def test_update_academic_stage_with_no_changes(app, admin_stage, admin_actor_id):
    with app.app_context():
        data = Data(
            name=admin_stage.name,
            display_order=admin_stage.display_order,
            is_active=admin_stage.is_active,
        )

        updated = update_academic_stage(data, admin_stage.id, admin_actor_id)

        assert updated is not None
        assert updated.id == admin_stage.id
        assert updated.name == admin_stage.name
        assert updated.display_order == admin_stage.display_order
        assert updated.is_active == admin_stage.is_active


# ======================================================================
# DELETE
# ======================================================================

def test_delete_academic_stage(app, admin_stage, admin_actor_id):
    stage_id = admin_stage.id

    with app.app_context():
        result = delete_academic_stage(stage_id, admin_actor_id)

        assert result is True
        assert db.session.get(AcademicStage, stage_id) is None


def test_delete_academic_stage_returns_false_when_missing(app, admin_actor_id):
    with app.app_context():
        result = delete_academic_stage(999999, admin_actor_id)

        assert result is False


def test_delete_academic_stage_with_levels_is_rejected(app, admin_stage, admin_actor_id):
    with app.app_context():
        stage = db.session.get(AcademicStage, admin_stage.id)

        if not hasattr(stage, "levels"):
            pytest.skip("AcademicStage model does not have a levels relationship.")

        try:
            level_model = AcademicStage.levels.property.mapper.class_
        except Exception:
            pytest.skip("Unable to determine the AcademicStage level model.")

        try:
            level = level_model(
               name="Test Level",
               stage_id=stage.id,
               school_id=stage.school_id,
           )
            db.session.add(level)
            db.session.commit()

        except Exception as exc:
            db.session.rollback()
            pytest.fail(
                 f"Could not create AcademicLevel for delete test: {exc}"
           )


        with pytest.raises(BadRequest) as exc:
            delete_academic_stage(stage.id, admin_actor_id)

        assert "Cannot delete academic stage" in exc.value.description
        assert "level(s) under it" in exc.value.description
