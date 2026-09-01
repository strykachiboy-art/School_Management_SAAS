import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from school_app.modules.promotion.services import promotion_rule_service as svc


def rule_data(**overrides):
    values = dict(
        name="Promotion Rule",
        from_level_id=1,
        to_level_id=2,
        min_average_score=50.0,
        min_attendance_percentage=75.0,
        min_subject_score=40.0,
        max_failed_subjects=2,
        requires_admin_approval=False,
        is_active=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_rule(**overrides):
    values = dict(
        id=10,
        school_id=1,
        name="Existing Rule",
        from_level_id=1,
        to_level_id=2,
        min_average_score=50.0,
        min_attendance_percentage=75.0,
        min_subject_score=40.0,
        max_failed_subjects=2,
        requires_admin_approval=False,
        is_active=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


# ======================================================================
# CREATE
# ======================================================================


def test_create_rule_requires_school_context():
    with pytest.raises(BadRequest):
        svc.create_promotion_rule(
            rule_data(),
            actor_id=7,
            school_id=None,
        )


def test_create_rule_rejects_missing_from_level(monkeypatch):
    monkeypatch.setattr(
        svc.db.session,
        "get",
        MagicMock(return_value=None),
    )

    with pytest.raises(NotFound):
        svc.create_promotion_rule(
            rule_data(from_level_id=99),
            actor_id=7,
            school_id=1,
        )


def test_create_rule_rejects_source_level_from_another_school(monkeypatch):
    level = SimpleNamespace(
        id=1,
        school_id=2,
        name="Level 1",
    )

    monkeypatch.setattr(
        svc.db.session,
        "get",
        MagicMock(return_value=level),
    )

    with pytest.raises(Forbidden):
        svc.create_promotion_rule(
            rule_data(),
            actor_id=7,
            school_id=1,
        )


def test_create_rule_rejects_target_level_from_another_school(monkeypatch):
    from_level = SimpleNamespace(
        id=1,
        school_id=1,
        name="Level 1",
    )

    to_level = SimpleNamespace(
        id=2,
        school_id=2,
        name="Level 2",
    )

    monkeypatch.setattr(
        svc.db.session,
        "get",
        MagicMock(side_effect=[from_level, to_level]),
    )

    with pytest.raises(Forbidden):
        svc.create_promotion_rule(
            rule_data(),
            actor_id=7,
            school_id=1,
        )


def test_create_active_rule_deactivates_existing_rule_for_same_school(
    monkeypatch,
):
    from_level = SimpleNamespace(
        id=1,
        school_id=1,
        name="Level 1",
    )

    to_level = SimpleNamespace(
        id=2,
        school_id=1,
        name="Level 2",
    )

    new_rule = MagicMock()
    new_rule.id = 20
    new_rule.name = "Promotion Rule"

    monkeypatch.setattr(
        svc.db.session,
        "get",
        MagicMock(side_effect=[from_level, to_level]),
    )

    mock_flush = MagicMock()
    mock_add = MagicMock()
    mock_commit = MagicMock()

    monkeypatch.setattr(svc.db.session, "flush", mock_flush)
    monkeypatch.setattr(svc.db.session, "add", mock_add)
    monkeypatch.setattr(svc.db.session, "commit", mock_commit)

    with patch.object(
        svc,
        "PromotionRule",
        return_value=new_rule,
    ), patch.object(
        svc,
        "_deactivate_existing_active_rule",
    ) as deactivate, patch.object(
        svc,
        "create_audit_log",
    ) as audit:

        result = svc.create_promotion_rule(
            rule_data(),
            actor_id=7,
            school_id=1,
        )

    assert result is new_rule

    deactivate.assert_called_once_with(1, 1)

    mock_add.assert_called_once_with(new_rule)
    mock_flush.assert_called_once()
    mock_commit.assert_called_once()

    audit.assert_called_once()


def test_create_inactive_rule_does_not_deactivate_existing_rule(
    monkeypatch,
):
    from_level = SimpleNamespace(
        id=1,
        school_id=1,
        name="Level 1",
    )

    to_level = SimpleNamespace(
        id=2,
        school_id=1,
        name="Level 2",
    )

    new_rule = MagicMock()
    new_rule.id = 21
    new_rule.name = "Promotion Rule"

    monkeypatch.setattr(
        svc.db.session,
        "get",
        MagicMock(side_effect=[from_level, to_level]),
    )

    mock_flush = MagicMock()
    mock_add = MagicMock()
    mock_commit = MagicMock()

    monkeypatch.setattr(svc.db.session, "flush", mock_flush)
    monkeypatch.setattr(svc.db.session, "add", mock_add)
    monkeypatch.setattr(svc.db.session, "commit", mock_commit)

    with patch.object(
        svc,
        "PromotionRule",
        return_value=new_rule,
    ), patch.object(
        svc,
        "_deactivate_existing_active_rule",
    ) as deactivate, patch.object(
        svc,
        "create_audit_log",
    ):

        result = svc.create_promotion_rule(
            rule_data(is_active=False),
            actor_id=7,
            school_id=1,
        )

    assert result is new_rule

    deactivate.assert_not_called()

    mock_add.assert_called_once_with(new_rule)
    mock_flush.assert_called_once()
    mock_commit.assert_called_once()


# ======================================================================
# READ
# ======================================================================


def test_get_all_rules_filters_by_school_and_level(monkeypatch, db_session):
    result = [make_rule()]

    scalars = MagicMock()
    scalars.all.return_value = result

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    rules = svc.get_all_promotion_rules(
        from_level_id=1,
        include_inactive=False,
        school_id=1,
    )

    assert rules == result
    db_session.scalars.assert_called_once()


def test_get_all_rules_can_include_inactive(monkeypatch, db_session):
    scalars = MagicMock()
    scalars.all.return_value = []

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    assert svc.get_all_promotion_rules(
        include_inactive=True,
        school_id=1,
    ) == []


def test_get_rule_is_school_scoped(monkeypatch, db_session):
    rule = make_rule()

    scalars = MagicMock()
    scalars.first.return_value = rule

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    assert svc.get_promotion_rule(
        10,
        school_id=1,
    ) is rule

    db_session.scalars.assert_called_once()


def test_get_rule_returns_none_when_not_found(monkeypatch, db_session):
    scalars = MagicMock()
    scalars.first.return_value = None

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    assert svc.get_promotion_rule(
        999,
        school_id=1,
    ) is None


def test_get_active_rule_for_level_is_school_scoped(
    monkeypatch,
    db_session,
):
    rule = make_rule()

    scalars = MagicMock()
    scalars.first.return_value = rule

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    assert svc.get_active_rule_for_level(
        1,
        school_id=1,
    ) is rule


# ======================================================================
# UPDATE
# ======================================================================


def test_update_rule_returns_none_when_rule_not_found(
    monkeypatch,
    db_session,
):
    scalars = MagicMock()
    scalars.first.return_value = None

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    assert svc.update_promotion_rule(
        rule_data(name="Updated"),
        999,
        actor_id=7,
        school_id=1,
    ) is None


def test_update_rule_changes_fields_and_audits(
    monkeypatch,
    db_session,
):
    rule = make_rule()

    scalars = MagicMock()
    scalars.first.return_value = rule

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    mock_flush = MagicMock()
    mock_commit = MagicMock()

    monkeypatch.setattr(
        db_session,
        "flush",
        mock_flush,
    )
    monkeypatch.setattr(
        db_session,
        "commit",
        mock_commit,
    )

    data = rule_data(
        name="Updated Rule",
        min_average_score=65.0,
        min_attendance_percentage=80.0,
        min_subject_score=45.0,
        max_failed_subjects=1,
        requires_admin_approval=True,
        is_active=True,
    )

    with patch.object(
        svc,
        "create_audit_log",
    ) as audit:

        result = svc.update_promotion_rule(
            data,
            10,
            actor_id=7,
            school_id=1,
        )

    assert result is rule

    assert rule.name == "Updated Rule"
    assert rule.min_average_score == 65.0
    assert rule.min_attendance_percentage == 80.0
    assert rule.min_subject_score == 45.0
    assert rule.max_failed_subjects == 1
    assert rule.requires_admin_approval is True

    audit.assert_called_once()


def test_update_inactive_rule_to_active_deactivates_existing_rule(
    monkeypatch,
    db_session,
):
    rule = make_rule(is_active=False)

    scalars = MagicMock()
    scalars.first.return_value = rule

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    monkeypatch.setattr(
        db_session,
        "flush",
        MagicMock(),
    )

    monkeypatch.setattr(
        db_session,
        "commit",
        MagicMock(),
    )

    with patch.object(
        svc,
        "_deactivate_existing_active_rule",
    ) as deactivate, patch.object(
        svc,
        "create_audit_log",
    ):

        svc.update_promotion_rule(
            rule_data(is_active=True),
            10,
            actor_id=7,
            school_id=1,
        )

    deactivate.assert_called_once_with(1, 1)


# ======================================================================
# DELETE
# ======================================================================


def test_delete_rule_returns_false_when_not_found(
    monkeypatch,
    db_session,
):
    scalars = MagicMock()
    scalars.first.return_value = None

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    assert svc.delete_promotion_rule(
        999,
        actor_id=7,
        school_id=1,
    ) is False


def test_delete_rule_deletes_and_audits(
    monkeypatch,
    db_session,
):
    rule = make_rule()

    scalars = MagicMock()
    scalars.first.return_value = rule

    monkeypatch.setattr(
        db_session,
        "scalars",
        MagicMock(return_value=scalars),
    )

    mock_delete = MagicMock()
    mock_commit = MagicMock()

    monkeypatch.setattr(
        db_session,
        "delete",
        mock_delete,
    )
    monkeypatch.setattr(
        db_session,
        "commit",
        mock_commit,
    )

    with patch.object(
        svc,
        "create_audit_log",
    ) as audit:

        assert svc.delete_promotion_rule(
            10,
            actor_id=7,
            school_id=1,
        ) is True

    mock_delete.assert_called_once_with(rule)
    mock_commit.assert_called_once()

    audit.assert_called_once()


# ======================================================================
# INTERNAL HELPERS
# ======================================================================


def test_deactivate_existing_active_rule_is_school_scoped(
    monkeypatch,
    db_session,
):
    mock_execute = MagicMock()

    monkeypatch.setattr(
        db_session,
        "execute",
        mock_execute,
    )

    svc._deactivate_existing_active_rule(
        3,
        school_id=7,
    )

    mock_execute.assert_called_once()

    statement = mock_execute.call_args.args[0]

    assert "promotion_rule" in str(statement).lower()
    assert "school_id" in str(statement).lower()


# ======================================================================
# SPECIAL CREATE CASE
# ======================================================================


def test_create_rule_with_no_target_level_is_allowed(monkeypatch):
    from_level = SimpleNamespace(
        id=1,
        school_id=1,
        name="Final Level",
    )

    new_rule = SimpleNamespace(
        id=30,
        name="Promotion Rule",
    )

    monkeypatch.setattr(
        svc.db.session,
        "get",
        MagicMock(return_value=from_level),
    )

    monkeypatch.setattr(
        svc.db.session,
        "flush",
        MagicMock(),
    )

    monkeypatch.setattr(
        svc.db.session,
        "add",
        MagicMock(),
    )

    monkeypatch.setattr(
        svc.db.session,
        "commit",
        MagicMock(),
    )

    with patch.object(
        svc,
        "_deactivate_existing_active_rule",
    ), patch.object(
        svc,
        "PromotionRule",
        autospec=True,
    ) as promotion_rule, patch.object(
        svc,
        "create_audit_log",
    ):

        promotion_rule.return_value = new_rule

        result = svc.create_promotion_rule(
            rule_data(to_level_id=None),
            actor_id=7,
            school_id=1,
        )

    assert result is new_rule
    promotion_rule.assert_called_once()