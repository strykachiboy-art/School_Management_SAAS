from types import SimpleNamespace

import pytest

from school_app.modules.grading.services.grading_system_service import (
    create_grading_rule,
    create_grading_system,
    delete_grading_rule,
    resolve_grade_for_score,
    update_grading_rule,
)


class Data:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_create_grading_rule_sets_school_context(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Rule School System",
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
                min_score=80,
                max_score=100,
                grade_point=4.0,
                remark="Distinction",
                display_order=1,
            ),
            admin_actor_id,
        )

        assert rule.school_id == school.id
        assert rule.grading_system_id == system.id
        assert rule.grade_name == "A"


def test_update_grading_rule_changes_values(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Update Rule System",
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

        updated = update_grading_rule(
            Data(
                grade_name="C+",
                min_score=55,
                max_score=59,
                grade_point=2.3,
                remark="Good Enough",
                display_order=2,
            ),
            rule.id,
            admin_actor_id,
        )

        assert updated.grade_name == "C+"
        assert updated.min_score == 55
        assert updated.max_score == 59
        assert updated.grade_point == 2.3
        assert updated.display_order == 2


def test_delete_grading_rule_returns_true_when_deleted(app, school, admin_actor_id):
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
                grade_name="D",
                min_score=40,
                max_score=49,
                grade_point=1.0,
                remark="Pass",
                display_order=4,
            ),
            admin_actor_id,
        )

        assert delete_grading_rule(rule.id, admin_actor_id) is True


def test_resolve_grade_for_score_returns_grade_by_default_system(app, school, admin_actor_id):
    with app.app_context():
        system = create_grading_system(
            Data(
                name="Default Score System",
                strategy="LETTER_GRADE",
                is_default=True,
                school_id=school.id,
            ),
            admin_actor_id,
        )

        create_grading_rule(
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

        grade_name, remark, ok = resolve_grade_for_score(64, school_id=school.id)

        assert ok is True
        assert grade_name == "B"
        assert remark == "Good"


def test_resolve_grade_for_score_returns_none_when_no_system_exists(app):
    with app.app_context():
        grade_name, remark, ok = resolve_grade_for_score(50, school_id=9999)

        assert grade_name is None
        assert remark is None
        assert ok is False
