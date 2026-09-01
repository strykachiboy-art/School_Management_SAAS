from datetime import datetime, timezone, timedelta
from typing import Optional
from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.excuses import Excuse
from school_app.models.attendance import Attendance
from school_app.enums.excuse import ExcuseStatus
from school_app.enums.attendance import AttendanceStatus
from school_app.modules.attendance.services.notification_excuse_service import (
    notify_excuse_decision,
)
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def _utcnow() -> datetime:
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)


# Excuses must be requested within this many days of the absence.
EXCUSE_REQUEST_WINDOW_DAYS = 7


def _assert_owns_excuse(excuse: Excuse, student_id: int) -> None:
    """Ensure the excuse belongs to the current student."""
    if not excuse.attendance:
        abort(400, description="Attendance record associated with excuse was not found.")
        
    if excuse.attendance.student_id != student_id:
        abort(
            403,
            description="You can only manage your own excuse requests.",
        )


def _get_attendance_or_raise(attendance_id: int) -> Attendance:
    attendance = db.session.get(Attendance, attendance_id)
    if not attendance:
        abort(
            404,
            description=f"Attendance record with ID {attendance_id} not found.",
        )

    return attendance


# ======================================================================
# 1. CREATE EXCUSE
# ======================================================================

def create_excuse(
    attendance_id: int,
    reason: str,
    student_id: int,
    actor_id: Optional[int] = None,
) -> Excuse:
    """
    Create an excuse for the authenticated student's absent attendance.
    school_id is inherited from Attendance because Attendance is the
    authoritative record connecting the student and school.
    """
    attendance = _get_attendance_or_raise(attendance_id)

    if attendance.student_id != student_id:
        abort(
            403,
            description="You can only submit an excuse for your own attendance record.",
        )

    if attendance.status != AttendanceStatus.ABSENT:
        abort(
            400,
            description=(
                "An excuse can only be submitted for an ABSENT "
                "attendance record."
            ),
        )

    days_since_absence = (_utcnow().date() - attendance.date).days

    if days_since_absence < 0:
        abort(
            400,
            description="An excuse cannot be submitted for a future attendance date.",
        )

    if days_since_absence > EXCUSE_REQUEST_WINDOW_DAYS:
        abort(
            400,
            description=(
                f"Excuses must be requested within "
                f"{EXCUSE_REQUEST_WINDOW_DAYS} days of the absence. "
                f"This absence was {days_since_absence} days ago."
            ),
        )

    existing_excuse = db.session.scalar(
        db.select(Excuse).where(
            Excuse.attendance_id == attendance_id
        )
    )

    if existing_excuse:
        abort(
            400,
            description=(
                "An excuse request already exists for this "
                "attendance record."
            ),
        )

    school_id = attendance.school_id

    if school_id is None:
        abort(
            400,
            description=(
                "The attendance record is not associated with a school."
            ),
        )

    excuse = Excuse(
        school_id=school_id,
        attendance_id=attendance_id,
        reason=reason,
        status=ExcuseStatus.PENDING,
    )

    db.session.add(excuse)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description=(
                "Could not create excuse due to a database "
                "constraint error."
            ),
        )

    effective_actor_id = (
        actor_id if actor_id is not None else student_id
    )

    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.CREATE,
            resource_type="Excuse",
            resource_id=excuse.id,
            description=(
                f"Created excuse request for attendance ID "
                f"{attendance_id}"
            ),
        )

    db.session.commit()

    return excuse


# ======================================================================
# 2. GET SINGLE EXCUSE
# ======================================================================

def get_excuse(excuse_id: int) -> Excuse:
    excuse = db.session.get(Excuse, excuse_id)
    if not excuse:
        abort(
            404,
            description=f"Excuse with ID {excuse_id} not found.",
        )

    return excuse


# ======================================================================
# 3. GET EXCUSES
# ======================================================================

def get_excuses(
    student_id: Optional[int] = None,
    term_id: Optional[int] = None,
    status: Optional[ExcuseStatus] = None,
    school_id: Optional[int] = None,
):
    """
    Return excuses with optional student, term, status and school filters.
    """
    stmt = (
        db.select(Excuse)
        .join(
            Attendance,
            Excuse.attendance_id == Attendance.id,
        )
    )

    if school_id is not None:
        stmt = stmt.where(
            Excuse.school_id == school_id
        )

    if student_id is not None:
        stmt = stmt.where(
            Attendance.student_id == student_id
        )

    if term_id is not None:
        stmt = stmt.where(
            Attendance.term_id == term_id
        )

    if status is not None:
        stmt = stmt.where(
            Excuse.status == status
        )

    stmt = stmt.order_by(
        Excuse.created_at.desc()
    )

    return db.session.scalars(stmt).all()


# ======================================================================
# 4. UPDATE EXCUSE
# ======================================================================

def update_excuse(
    excuse_id: int,
    reason: str,
    student_id: int,
    actor_id: Optional[int] = None,
) -> Excuse:
    excuse = get_excuse(excuse_id)

    _assert_owns_excuse(
        excuse,
        student_id,
    )

    if excuse.status != ExcuseStatus.PENDING:
        abort(
            400,
            description=(
                f"Cannot update excuse with status "
                f"'{excuse.status.value}'. "
                "Only PENDING excuses can be modified."
            ),
        )

    changes = {}

    if reason != excuse.reason:
        changes["reason"] = {
            "before": excuse.reason,
            "after": reason,
        }

    excuse.reason = reason

    db.session.flush()

    effective_actor_id = (
        actor_id if actor_id is not None else student_id
    )

    if changes and effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.UPDATE,
            resource_type="Excuse",
            resource_id=excuse.id,
            description=(
                f"Updated excuse request ID {excuse.id}"
            ),
            changes=changes,
        )

    db.session.commit()

    return excuse


# ======================================================================
# 5. DELETE EXCUSE
# ======================================================================

def delete_excuse(
    excuse_id: int,
    student_id: int,
    actor_id: Optional[int] = None,
) -> bool:
    excuse = get_excuse(excuse_id)

    _assert_owns_excuse(
        excuse,
        student_id,
    )

    if excuse.status != ExcuseStatus.PENDING:
        abort(
            400,
            description=(
                f"Cannot delete excuse with status "
                f"'{excuse.status.value}'. "
                "Only PENDING excuses can be deleted."
            ),
        )

    db.session.delete(excuse)

    effective_actor_id = (
        actor_id if actor_id is not None else student_id
    )

    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.DELETE,
            resource_type="Excuse",
            resource_id=excuse_id,
            description=(
                f"Deleted excuse request ID {excuse_id}"
            ),
        )

    db.session.commit()

    return True


# ======================================================================
# 6. APPROVE EXCUSE
# ======================================================================

def approve_excuse(
    excuse_id: int,
    reviewer_id: int,
    actor_id: Optional[int] = None,
) -> Excuse:
    excuse = get_excuse(excuse_id)

    if excuse.status != ExcuseStatus.PENDING:
        abort(
            400,
            description=(
                f"Cannot approve excuse with status "
                f"'{excuse.status.value}'. "
                "Only PENDING excuses can be reviewed."
            ),
        )

    old_status = excuse.status.value

    excuse.status = ExcuseStatus.APPROVED
    excuse.reviewed_by = reviewer_id
    excuse.reviewed_at = _utcnow()

    # Approved excuse changes the attendance status to EXCUSED.
    excuse.attendance.status = AttendanceStatus.EXCUSED

    db.session.flush()

    notify_excuse_decision(excuse)

    effective_actor_id = (
        actor_id if actor_id is not None else reviewer_id
    )

    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.UPDATE,
            resource_type="Excuse",
            resource_id=excuse.id,
            description=(
                f"Approved excuse request ID {excuse.id}"
            ),
            changes={
                "status": {
                    "before": old_status,
                    "after": ExcuseStatus.APPROVED.value,
                }
            },
        )

    db.session.commit()

    return excuse


# ======================================================================
# 7. REJECT EXCUSE
# ======================================================================

def reject_excuse(
    excuse_id: int,
    reviewer_id: int,
    actor_id: Optional[int] = None,
) -> Excuse:
    excuse = get_excuse(excuse_id)

    if excuse.status != ExcuseStatus.PENDING:
        abort(
            400,
            description=(
                f"Cannot reject excuse with status "
                f"'{excuse.status.value}'. "
                "Only PENDING excuses can be reviewed."
            ),
        )

    old_status = excuse.status.value

    excuse.status = ExcuseStatus.REJECTED
    excuse.reviewed_by = reviewer_id
    excuse.reviewed_at = _utcnow()

    # Rejected excuse leaves attendance as ABSENT.
    excuse.attendance.status = AttendanceStatus.ABSENT

    db.session.flush()

    notify_excuse_decision(excuse)

    effective_actor_id = (
        actor_id if actor_id is not None else reviewer_id
    )

    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.UPDATE,
            resource_type="Excuse",
            resource_id=excuse.id,
            description=(
                f"Rejected excuse request ID {excuse.id}"
            ),
            changes={
                "status": {
                    "before": old_status,
                    "after": ExcuseStatus.REJECTED.value,
                }
            },
        )

    db.session.commit()

    return excuse


# ======================================================================
# 8. BULK REVIEW
# ======================================================================

def bulk_review_excuses(
    excuse_ids: list,
    decision: ExcuseStatus,
    reviewer_id: int,
    actor_id: Optional[int] = None,
) -> dict:
    if decision not in (
        ExcuseStatus.APPROVED,
        ExcuseStatus.REJECTED,
    ):
        abort(
            400,
            description=(
                "decision must be either 'approved' "
                "or 'rejected'."
            ),
        )

    excuses = db.session.scalars(
        db.select(Excuse).where(
            Excuse.id.in_(excuse_ids)
        )
    ).all()

    found_ids = {
        excuse.id
        for excuse in excuses
    }

    not_found = [
        excuse_id
        for excuse_id in excuse_ids
        if excuse_id not in found_ids
    ]

    reviewed = []
    reviewed_excuses = []
    skipped = []

    reviewed_at = _utcnow()

    for excuse in excuses:
        if excuse.status != ExcuseStatus.PENDING:
            skipped.append(
                {
                    "excuse_id": excuse.id,
                    "reason": (
                        f"already {excuse.status.value}"
                    ),
                }
            )
            continue

        excuse.status = decision
        excuse.reviewed_by = reviewer_id
        excuse.reviewed_at = reviewed_at

        excuse.attendance.status = (
            AttendanceStatus.EXCUSED
            if decision == ExcuseStatus.APPROVED
            else AttendanceStatus.ABSENT
        )

        reviewed.append(excuse.id)
        reviewed_excuses.append(excuse)

    db.session.flush()

    for excuse in reviewed_excuses:
        notify_excuse_decision(excuse)

    effective_actor_id = (
        actor_id if actor_id is not None else reviewer_id
    )

    if reviewed and effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.BULK_ACTION,
            resource_type="Excuse",
            resource_id=None,
            description=(
                f"Bulk reviewed {len(reviewed)} "
                f"excuse request(s) as {decision.value}"
            ),
            changes={
                "reviewed_excuse_ids": reviewed,
                "decision": decision.value,
            },
        )

    db.session.commit()

    return {
        "reviewed": reviewed,
        "skipped": skipped,
        "not_found": not_found,
    }