import pytest
from school_app.extensions import db
from school_app.enums.audit import AuditAction
from school_app.modules.audit.services.audit_log_service import create_audit_log


def test_list_audit_logs_unauthorized(client):
    response = client.get("/audit-logs")
    assert response.status_code == 401


def test_list_audit_logs_forbidden_for_teacher(client, teacher_headers):
    response = client.get("/audit-logs", headers=teacher_headers)
    assert response.status_code == 403


def test_list_audit_logs_success(client, admin_headers, base_user):
    create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.UPDATE,
        resource_type="Subject",
        resource_id=3,
        description="Updated subject name",
    )

    response = client.get("/audit-logs", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1


def test_list_audit_logs_validation_error(client, admin_headers):
    response = client.get("/audit-logs?page=-5", headers=admin_headers)
    assert response.status_code == 422

    data = response.get_json()
    assert "details" in data


def test_get_single_audit_log_success(client, admin_headers, base_user):
    log = create_audit_log(
        actor_id=base_user.id,
        action=AuditAction.CREATE,
        resource_type="Teacher",
        resource_id=7,
        description="Created teacher record",
    )

    response = client.get(f"/audit-logs/{log.id}", headers=admin_headers)
    assert response.status_code == 200

    data = response.get_json()
    assert data["id"] == log.id
    assert data["resource_type"] == "Teacher"


def test_get_single_audit_log_not_found(client, admin_headers):
    response = client.get("/audit-logs/99999", headers=admin_headers)
    assert response.status_code == 404