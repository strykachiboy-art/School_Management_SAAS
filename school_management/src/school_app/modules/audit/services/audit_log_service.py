from datetime import datetime
from typing import Optional

from school_app.extensions import db
from school_app.models.audit_log import AuditLog
from school_app.enums.audit import AuditAction


def create_audit_log(
    actor_id: Optional[int],
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[int],
    description: str,
    changes: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Creates and flushes a new audit log entry to generate an ID without committing."""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        description=description,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.session.add(log)
    db.session.flush() 
    return log


def get_audit_log(log_id: int) -> Optional[AuditLog]:
    """Retrieves a single audit log by its primary key."""
    return db.session.get(AuditLog, log_id)


def get_filtered_audit_logs(
    actor_id: Optional[int] = None,
    system_only: Optional[bool] = None,
    action: Optional[AuditAction] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 20,
):
    """Dynamically queries audit logs based on any combination of filter parameters."""
    stmt = db.select(AuditLog)

    if actor_id is not None:
        stmt = stmt.filter_by(actor_id=actor_id)
    if system_only is True:
        stmt = stmt.filter(AuditLog.actor_id.is_(None))
    elif system_only is False:
        stmt = stmt.filter(AuditLog.actor_id.is_not(None))
    if action is not None:
        stmt = stmt.filter_by(action=action)
    if resource_type is not None:
        stmt = stmt.filter_by(resource_type=resource_type)
    if resource_id is not None:
        stmt = stmt.filter_by(resource_id=resource_id)
    if date_from is not None:
        stmt = stmt.filter(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.filter(AuditLog.created_at <= date_to)

    stmt = stmt.order_by(AuditLog.created_at.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


# ============================== Legacy Helpers (Optional) ==============================

def get_all_audit_logs(page: int = 1, per_page: int = 20):
    stmt = db.select(AuditLog).order_by(AuditLog.created_at.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_audit_logs_by_actor(actor_id: int, page: int = 1, per_page: int = 20):
    stmt = db.select(AuditLog).filter_by(actor_id=actor_id).order_by(AuditLog.created_at.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_audit_logs_by_resource(
    resource_type: str, resource_id: int, page: int = 1, per_page: int = 20
):
    stmt = db.select(AuditLog).filter_by(resource_type=resource_type, resource_id=resource_id).order_by(AuditLog.created_at.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_audit_logs_by_action(action: AuditAction, page: int = 1, per_page: int = 20):
    stmt = db.select(AuditLog).filter_by(action=action).order_by(AuditLog.created_at.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


def get_audit_logs_by_date_range(
    date_from: datetime, date_to: datetime, page: int = 1, per_page: int = 20
):
    stmt = db.select(AuditLog).filter(
        AuditLog.created_at >= date_from, AuditLog.created_at <= date_to
    ).order_by(AuditLog.created_at.desc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)