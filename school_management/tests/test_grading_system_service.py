from types import SimpleNamespace

import pytest

from school_app.modules.grading.services.grading_system_service import (
    create_grading_rule,
    create_grading_system,
    delete_grading_rule,
    delete_grading_system,
    get_all_grading_systems,
    get_default_grading_system,
    get_grading_system,
    resolve_grade_for_score,
    update_grading_rule,
    update_grading_system,
)


class Data:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_create_grading_system_success(app, school, admin_actor_id):
    with app.app_context():
        data = Data(
            name="Progressive Grading",
            strategy="LETTER_GRADE",
            is_default=True,
            school_id=school.id,
        )

        system = create_grading_system(data, admin_actor_id)

        assert system.id is not None
        assert system.name == "Progressive Grading"
        assert system.school_id == school.id
        assert system.is_default is True


def test_create_grading_system_replaces_default_for_same_school(app, school, admin_actor_id):
    with app.app_context():
        first = create_grading_system(
            Data(
                name="First System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        second = create_grading_system(
            Data(
                name="Second System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        assert first.is_default is False
        assert second.is_default is True
        assert get_default_grading_system(school.id).id == second.id


def test_get_all_grading_systems_only_returns_active_by_default(app, school, admin_actor_id):
    with app.app_context():
        active = create_grading_system(
            Data(
                name="Active System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
                is_active=True,
            ),
            admin_actor_id,
        )
        inactive = create_grading_system(
            Data(
                name="Inactive System",
                strategy="LETTER_GRADE",
                is_default=False,
                school_id=school.id,
                is_active=False,
            ),
            admin_actor_id,
        )

        systems = get_all_grading_systems()
        ids = [system.id for system in systems]

        assert active.id in ids
        assert inactive.id not in ids


def test_get_grading_system_returns_none_for_missing_id(app):
    with app.app_context():
        assert get_grading_system(999999) is None


def test_update_grading_system_success(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Before",
                strategy="LETTER_GRADE",
                is_default=False,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        updated = update_grading_system(
            Data(
                name="After",
                strategy="PERCENTAGE",
                is_default=True,
                is_active=False,
            ),
            system.id,
            admin_actor_id,
        )

        assert updated is not None
        assert updated.name == "After"
        assert updated.strategy.value == "PERCENTAGE"
        assert updated.is_default is True
        assert updated.is_active is False


def test_delete_grading_system_rejects_default_system(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Default System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        with pytest.raises(Exception):
            delete_grading_system(system.id, admin_actor_id)


def test_delete_grading_system_removes_non_default_system(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Secondary System",
                strategy="LETTER_GRADE",
                is_default=False,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        result = delete_grading_system(system.id, admin_actor_id)

        assert result is True
        assert get_grading_system(system.id) is None


def test_create_grading_rule_success(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="School System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        rule = create_grading_rule(
            Data(
                grading_system_id=system.id,
                grade_name="A",
                min_score=70,
                max_score=100,
                grade_point=4.0,
                remark="Excellent",
                display_order=1,
            ),
            admin_actor_id,
        )

        assert rule.id is not None
        assert rule.grading_system_id == system.id
        assert rule.school_id == school.id
        assert rule.grade_name == "A"


def test_create_grading_rule_rejects_missing_system(app, school, admin_actor_id):
    with app.app_context():
        with pytest.raises(Exception):
            create_grading_rule(
                Data(
                    grading_system_id=999999,
                    grade_name="A",
                    min_score=70,
                    max_score=100,
                    display_order=1,
                ),
                admin_actor_id,
            )


def test_update_grading_rule_success(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Update System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        rule = create_grading_rule(
            Data(
                grading_system_id=system.id,
                grade_name="B",
                min_score=60,
                max_score=69,
                grade_point=3.0,
                remark="Good",
                display_order=2,
            ),
            admin_actor_id,
        )

        updated = update_grading_rule(
            Data(
                grade_name="B+",
                min_score=65,
                max_score=69,
                grade_point=3.5,
                remark="Very Good",
                display_order=1,
            ),
            rule.id,
            admin_actor_id,
        )

        assert updated is not None
        assert updated.grade_name == "B+"
        assert updated.min_score == 65
        assert updated.grade_point == 3.5
        assert updated.display_order == 1


def test_delete_grading_rule_removes_rule(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Delete Rule System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        rule = create_grading_rule(
            Data(
                grading_system_id=system.id,
                grade_name="C",
                min_score=50,
                max_score=59,
                grade_point=2.0,
                remark="Fair",
                display_order=3,
            ),
            admin_actor_id,
        )

        assert delete_grading_rule(rule.id, admin_actor_id) is True


def test_resolve_grade_for_score_uses_school_default_system(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Score System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        create_grading_rule(
            Data(
                grading_system_id=system.id,
                grade_name="A",
                min_score=70,
                max_score=100,
                grade_point=4.0,
                remark="Excellent",
                display_order=1,
            ),
            admin_actor_id,
        )

        grade_name, remark, ok = resolve_grade_for_score(82, school_id=school.id)

        assert ok is True
        assert grade_name == "A"
        assert remark == "Excellent"
