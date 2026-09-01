from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from school_app.modules.promotion.requests.promotion_rule_request import (
    PromotionRuleCreateRequest,
    PromotionRuleUpdateRequest,
)

from school_app.modules.promotion.routes import promotion_rule_route as promotion_rule_routes


def response_rule(**overrides):
    values = dict(
        id=1,
        school_id=1,
        name="Promotion Rule",
        from_level_id=1,
        to_level_id=2,
        min_average_score=50.0,
        min_attendance_percentage=75.0,
        min_subject_score=40.0,
        max_failed_subjects=2,
        requires_admin_approval=False,
        is_active=True,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_create_rule_admin_success(app, admin_headers):
    client = app.test_client()
    rule = response_rule()

    with patch.object(promotion_rule_routes, "create_promotion_rule", return_value=rule) as create:
        response = client.post(
            "/promotion-rules/create",
            json={
                "name": "Promotion Rule",
                "from_level_id": 1,
                "to_level_id": 2,
                "min_average_score": 50,
                "min_attendance_percentage": 75,
                "min_subject_score": 40,
                "max_failed_subjects": 2,
                "requires_admin_approval": False,
                "is_active": True,
            },
            headers=admin_headers,
        )

    assert response.status_code == 201
    create.assert_called_once()
    assert response.get_json()["id"] == 1


def test_create_rule_teacher_forbidden(app, teacher_headers):
    response = app.test_client().post(
        "/promotion-rules/create",
        json={"name": "Promotion Rule", "from_level_id": 1},
        headers=teacher_headers,
    )
    assert response.status_code in (401, 403)


def test_create_rule_validation_error(app, admin_headers):
    response = app.test_client().post(
        "/promotion-rules/create",
        json={"name": "x", "from_level_id": 1},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_get_all_rules_admin(app, admin_headers):
    rule = response_rule()
    with patch.object(promotion_rule_routes, "get_all_promotion_rules", return_value=[rule]) as get_all:
        response = app.test_client().get(
            "/promotion-rules",
            headers=admin_headers,
        )

    assert response.status_code == 200
    assert response.get_json()[0]["id"] == 1
    get_all.assert_called_once()


def test_get_all_rules_teacher(app, teacher_headers):
    with patch.object(promotion_rule_routes, "get_all_promotion_rules", return_value=[]) as get_all:
        response = app.test_client().get(
            "/promotion-rules?from_level_id=3&include_inactive=true",
            headers=teacher_headers,
        )

    assert response.status_code == 200
    get_all.assert_called_once()
    kwargs = get_all.call_args.kwargs
    assert kwargs["from_level_id"] == 3
    assert kwargs["include_inactive"] is True


def test_get_all_rules_student_forbidden(app, student_headers):
    response = app.test_client().get(
        "/promotion-rules",
        headers=student_headers,
    )
    assert response.status_code in (401, 403)


def test_get_rule_success(app, admin_headers):
    rule = response_rule()
    with patch.object(promotion_rule_routes, "get_promotion_rule", return_value=rule):
        response = app.test_client().get(
            "/promotion-rules/1",
            headers=admin_headers,
        )

    assert response.status_code == 200
    assert response.get_json()["name"] == "Promotion Rule"


def test_get_rule_not_found(app, admin_headers):
    with patch.object(promotion_rule_routes, "get_promotion_rule", return_value=None):
        response = app.test_client().get(
            "/promotion-rules/999",
            headers=admin_headers,
        )

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["PUT", "PATCH"])
def test_update_rule_success(app, admin_headers, method):
    rule = response_rule(name="Updated Rule")

    with patch.object(promotion_rule_routes, "update_promotion_rule", return_value=rule) as update:
        response = app.test_client().open(
            "/promotion-rules/1/edit",
            method=method,
            json={"name": "Updated Rule"},
            headers=admin_headers,
        )

    assert response.status_code == 200
    assert response.get_json()["name"] == "Updated Rule"
    update.assert_called_once()


def test_update_rule_teacher_forbidden(app, teacher_headers):
    response = app.test_client().patch(
        "/promotion-rules/1/edit",
        json={"name": "Updated Rule"},
        headers=teacher_headers,
    )
    assert response.status_code in (401, 403)


def test_update_rule_not_found(app, admin_headers):
    with patch.object(promotion_rule_routes, "update_promotion_rule", return_value=None):
        response = app.test_client().patch(
            "/promotion-rules/999/edit",
            json={"name": "Updated Rule"},
            headers=admin_headers,
        )

    assert response.status_code == 404


def test_delete_rule_success(app, admin_headers):
    with patch.object(promotion_rule_routes, "delete_promotion_rule", return_value=True) as delete:
        response = app.test_client().delete(
            "/promotion-rules/1",
            headers=admin_headers,
        )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Promotion rule deleted successfully"
    }
    delete.assert_called_once()


def test_delete_rule_not_found(app, admin_headers):
    with patch.object(promotion_rule_routes, "delete_promotion_rule", return_value=False):
        response = app.test_client().delete(
            "/promotion-rules/999",
            headers=admin_headers,
        )

    assert response.status_code == 404


def test_delete_rule_teacher_forbidden(app, teacher_headers):
    response = app.test_client().delete(
        "/promotion-rules/1",
        headers=teacher_headers,
    )
    assert response.status_code in (401, 403)


def test_route_forwards_school_context(app, admin_headers):
    rule = response_rule()

    with patch.object(promotion_rule_routes, "get_promotion_rule", return_value=rule) as get_rule:
        response = app.test_client().get(
            "/promotion-rules/1",
            headers=admin_headers,
        )

    assert response.status_code == 200
    kwargs = get_rule.call_args.kwargs
    assert kwargs["school_id"] == rule.school_id
