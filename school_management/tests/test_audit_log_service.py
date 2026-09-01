from datetime import datetime, timedelta, timezone

from school_app.enums.audit import AuditAction
from school_app.extensions import db
from school_app.modules.audit.services.audit_log_service import (
    create_audit_log,
    get_audit_log,
    get_filtered_audit_logs,
)


# ============================== Create ==============================

def test_create_audit_log_success(base_user, school):
    log = create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Subject",
        resource_id=1,
        description="Created a new test subject",
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
    )
    assert log.id is not None
    assert log.school_id == school.id
    assert log.actor_id == base_user.id
    assert log.action == AuditAction.CREATE
    assert log.resource_type == "Subject"
    assert log.resource_id == 1


def test_create_audit_log_with_no_actor(school):
    """System/webhook events may have no logged-in actor."""
    log = create_audit_log(
        school_id=school.id,
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Payment",
        resource_id=99,
        description="Gateway rejected transaction",
    )
    assert log.id is not None
    assert log.school_id == school.id
    assert log.actor_id is None
    assert log.action == AuditAction.PAYMENT_FAILED


def test_create_platform_audit_log_without_school():
    """Platform-level/super-admin events may intentionally have no school."""
    log = create_audit_log(
        school_id=None,
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Platform",
        resource_id=None,
        description="Platform-level system event",
    )
    assert log.id is not None
    assert log.school_id is None
    assert log.actor_id is None


# ============================== Get ==============================

def test_get_audit_log_found(base_user, school):
    log = create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.UPDATE,
        resource_type="Student",
        resource_id=5,
        description="Updated student details",
    )
    fetched = get_audit_log(log.id)

    assert fetched is not None
    assert fetched.id == log.id
    assert fetched.school_id == school.id


def test_get_audit_log_not_found():
    fetched = get_audit_log(99999)
    assert fetched is None


# ============================== Filtering ==============================

def test_get_filtered_audit_logs(base_user, school):
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Classroom",
        resource_id=10,
        description="Created classroom",
    )
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.DELETE,
        resource_type="Classroom",
        resource_id=10,
        description="Deleted classroom",
    )

    result = get_filtered_audit_logs(
        action=AuditAction.DELETE,
        page=1,
        per_page=10,
    )

    assert result.total == 1
    assert result.items[0].action == AuditAction.DELETE
    assert result.items[0].school_id == school.id

    result_res = get_filtered_audit_logs(
        resource_type="Classroom",
        page=1,
        per_page=10,
    )

    assert result_res.total >= 2


def test_get_filtered_audit_logs_by_school(base_user, school):
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Student",
        resource_id=1,
        description="School student created",
    )
    result = get_filtered_audit_logs(
        school_id=school.id,
        page=1,
        per_page=10,
    )

    assert result.total == 1
    assert result.items[0].school_id == school.id


def test_get_filtered_audit_logs_does_not_return_other_school_logs(
    base_user,
    school,
    app,
):
    from school_app.models.school import School
    with app.app_context():
        other_school = School(
            name="Other Test School",
            slug="other-test-school",
        )

        db.session.add(other_school)
        db.session.commit()

        create_audit_log(
            school_id=school.id,
            actor_id=base_user.id,
            action=AuditAction.CREATE,
            resource_type="Student",
            resource_id=1,
            description="First school log",
        )

        create_audit_log(
            school_id=other_school.id,
            actor_id=None,
            action=AuditAction.CREATE,
            resource_type="Student",
            resource_id=2,
            description="Other school log",
        )

        result = get_filtered_audit_logs(
            school_id=school.id,
            page=1,
            per_page=10,
        )

        assert result.total == 1
        assert result.items[0].school_id == school.id


# ============================== System / Human Filtering ==============================

def test_get_filtered_audit_logs_system_only(base_user, school):
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Payment",
        resource_id=1,
        description="Human-recorded payment",
    )
    create_audit_log(
        school_id=school.id,
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Payment",
        resource_id=2,
        description="Gateway rejected transaction",
    )

    system_result = get_filtered_audit_logs(
        school_id=school.id,
        system_only=True,
        page=1,
        per_page=10,
    )

    assert system_result.total == 1
    assert system_result.items[0].actor_id is None
    assert system_result.items[0].school_id == school.id

    human_result = get_filtered_audit_logs(
        school_id=school.id,
        system_only=False,
        page=1,
        per_page=10,
    )

    assert human_result.total == 1
    assert human_result.items[0].actor_id == base_user.id
    assert human_result.items[0].school_id == school.id


def test_get_filtered_audit_logs_system_only_none_means_no_filter(
    base_user,
    school,
):
    """None must not filter by actor presence."""
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Payment",
        resource_id=3,
        description="Human-recorded payment",
    )
    create_audit_log(
        school_id=school.id,
        actor_id=None,
        action=AuditAction.PAYMENT_FAILED,
        resource_type="Payment",
        resource_id=4,
        description="Gateway rejected transaction",
    )

    result = get_filtered_audit_logs(
        school_id=school.id,
        page=1,
        per_page=10,
    )

    assert result.total == 2


# ============================== Combined Filters ==============================

def test_get_filtered_audit_logs_by_school_and_action(base_user, school):
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Student",
        resource_id=1,
        description="Created student",
    )
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.DELETE,
        resource_type="Student",
        resource_id=1,
        description="Deleted student",
    )

    result = get_filtered_audit_logs(
        school_id=school.id,
        action=AuditAction.DELETE,
        page=1,
        per_page=10,
    )

    assert result.total == 1
    assert result.items[0].school_id == school.id
    assert result.items[0].action == AuditAction.DELETE


def test_get_filtered_audit_logs_by_resource(base_user, school):
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Classroom",
        resource_id=10,
        description="Created classroom",
    )
    create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.UPDATE,
        resource_type="Classroom",
        resource_id=10,
        description="Updated classroom",
    )

    result = get_filtered_audit_logs(
        school_id=school.id,
        resource_type="Classroom",
        resource_id=10,
        page=1,
        per_page=10,
    )

    assert result.total == 2

    for log in result.items:
        assert log.school_id == school.id
        assert log.resource_type == "Classroom"
        assert log.resource_id == 10


# ============================== Date Filtering ==============================

def test_get_filtered_audit_logs_by_date_range(base_user, school):
    log = create_audit_log(
        school_id=school.id,
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Student",
        resource_id=20,
        description="Created student",
    )
    now = datetime.now(timezone.utc)

    result = get_filtered_audit_logs(
        school_id=school.id,
        date_from=now - timedelta(minutes=1),
        date_to=now + timedelta(minutes=1),
        page=1,
        per_page=10,
    )

    assert result.total == 1
    assert result.items[0].id == log.id
    assert result.items[0].school_id == school.id