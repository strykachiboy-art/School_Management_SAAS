from datetime import datetime, timezone, timedelta
from school_app.extensions import db
from school_app.enums.audit import AuditAction
from school_app.modules.audit.services.audit_log_service import (
    create_audit_log,
    get_audit_log,
    get_filtered_audit_logs,
)


def test_create_audit_log_success(base_user):
    log = create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Subject",
        resource_id=1,
        description="Created a new test subject",
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
    )
    
    assert log.id is not None
    assert log.actor_id == base_user.id
    assert log.action == AuditAction.CREATE
    assert log.resource_type == "Subject"
    assert log.resource_id == 1


def test_get_audit_log_found(base_user):
    log = create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.UPDATE,
        resource_type="Student",
        resource_id=5,
        description="Updated student details",
    )
    
    fetched = get_audit_log(log.id)
    assert fetched is not None
    assert fetched.id == log.id


def test_get_filtered_audit_logs(base_user):
    create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Classroom",
        resource_id=10,
        description="Created classroom",
    )
    create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.DELETE,
        resource_type="Classroom",
        resource_id=10,
        description="Deleted classroom",
    )

    result = get_filtered_audit_logs(action=AuditAction.DELETE, page=1, per_page=10)
    assert result.total == 1
    assert result.items[0].action == AuditAction.DELETE

    result_res = get_filtered_audit_logs(resource_type="Classroom", page=1, per_page=10)
    assert result_res.total >= 2


def test_create_audit_log_with_no_actor(base_user):
    """Gateway/webhook-driven entries (e.g. PAYMENT_FAILED) have no
    logged-in user — actor_id must accept None since AuditLog.actor_id
    was made nullable for exactly this case."""
    log = create_audit_log(
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Payment",
        resource_id=99,
        description="Gateway rejected transaction",
    )

    assert log.id is not None
    assert log.actor_id is None
    assert log.action == AuditAction.PAYMENT_FAILED


def test_get_filtered_audit_logs_system_only(base_user):
    create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Payment",
        resource_id=1,
        description="Human-recorded payment",
    )
    create_audit_log(
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Payment",
        resource_id=2,
        description="Gateway rejected transaction",
    )

    system_result = get_filtered_audit_logs(system_only=True, page=1, per_page=10)
    assert system_result.total == 1
    assert system_result.items[0].actor_id is None

    human_result = get_filtered_audit_logs(system_only=False, page=1, per_page=10)
    assert human_result.total == 1
    assert human_result.items[0].actor_id == base_user.id


def test_get_filtered_audit_logs_system_only_none_means_no_filter(base_user):
    """Omitting system_only (the default, None) must not filter at all —
    only explicit True/False should narrow by actor presence."""
    create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Payment",
        resource_id=3,
        description="Human-recorded payment",
    )
    create_audit_log(
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Payment",
        resource_id=4,
        description="Gateway rejected transaction",
    )

    result = get_filtered_audit_logs(page=1, per_page=10)
    assert result.total == 2