from flask import abort
from school_app.extensions import db
from school_app.models.term import Term
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


class TermValidationError(Exception):
    """Raised when a Term violates a business rule."""
    pass


# =========================== validation helpers =================================

def _check_unique_name(academic_session_id, name, exclude_term_id=None):
    """Rule 1: name must be unique within its academic session."""
    stmt = db.select(Term).where(
        Term.academic_session_id == academic_session_id, Term.name == name
    )
    if exclude_term_id:
        stmt = stmt.where(Term.id != exclude_term_id)

    if db.session.scalars(stmt).first():
        raise TermValidationError(
            f'A term named "{name}" already exists in this academic session.'
        )


def _check_no_overlap(academic_session_id, start_date, end_date, exclude_term_id=None):
    """Rule 2: date range must not overlap another term in the same session."""
    if start_date >= end_date:
        raise TermValidationError("start_date must be before end_date.")

    stmt = db.select(Term).where(
        Term.academic_session_id == academic_session_id,
        Term.start_date < end_date,
        Term.end_date > start_date,
    )
    if exclude_term_id:
        stmt = stmt.where(Term.id != exclude_term_id)

    overlapping = db.session.scalars(stmt).first()
    if overlapping:
        raise TermValidationError(
            f'Dates overlap with existing term "{overlapping.name}" '
            f'({overlapping.start_date} - {overlapping.end_date}).'
        )


def _unset_other_current_terms(academic_session_id, exclude_term_id=None):
    """Rule 3: only one term per session may be is_current=True."""
    stmt = db.update(Term).where(
        Term.academic_session_id == academic_session_id, Term.is_current.is_(True)
    )
    if exclude_term_id:
        stmt = stmt.where(Term.id != exclude_term_id)

    db.session.execute(stmt.values(is_current=False))


# ============================ create term ============================

def create_term(data, actor_id):
    try:
        _check_unique_name(data.academic_session_id, data.name)
        _check_no_overlap(data.academic_session_id, data.start_date, data.end_date)
    except TermValidationError as e:
        abort(400, description=str(e))

    term = Term(
        academic_session_id=data.academic_session_id,
        name=data.name,
        start_date=data.start_date,
        end_date=data.end_date,
        is_current=data.is_current or False,
    )
    db.session.add(term)
    db.session.flush()

    if term.is_current:
        _unset_other_current_terms(data.academic_session_id, exclude_term_id=term.id)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="Term",
        resource_id=term.id,
        description=f"Created term {term.name}",
    )

    db.session.commit()
    return term


# =============================== get all terms =============================

def get_all_term(search="", page=1, per_page=10):
    stmt = db.select(Term)
    if search:
        stmt = stmt.where(Term.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Term.start_date.desc())

    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


# ============================== get term ===================================

def get_term_by_id(term_id):
    return db.session.get(Term, term_id)


# ============================== update term =================================

def update_term(data, term_id, actor_id):
    term = db.session.get(Term, term_id)
    if term is None:
        return None

    new_name = data.name if data.name is not None else term.name
    new_start = data.start_date if data.start_date is not None else term.start_date
    new_end = data.end_date if data.end_date is not None else term.end_date

    try:
        if data.name is not None:
            _check_unique_name(term.academic_session_id, new_name, exclude_term_id=term.id)
        if data.start_date is not None or data.end_date is not None:
            _check_no_overlap(term.academic_session_id, new_start, new_end, exclude_term_id=term.id)
    except TermValidationError as e:
        abort(400, description=str(e))

    changes = {}
    if new_name != term.name:
        changes["name"] = {"before": term.name, "after": new_name}
    if new_start != term.start_date:
        changes["start_date"] = {"before": str(term.start_date), "after": str(new_start)}
    if new_end != term.end_date:
        changes["end_date"] = {"before": str(term.end_date), "after": str(new_end)}

    term.name = new_name
    term.start_date = new_start
    term.end_date = new_end

    if data.is_current is True:
        _unset_other_current_terms(term.academic_session_id, exclude_term_id=term.id)
        term.is_current = True
        changes["is_current"] = {"before": False, "after": True}
    elif data.is_current is False:
        if term.is_current:
            changes["is_current"] = {"before": True, "after": False}
        term.is_current = False

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Term",
            resource_id=term.id,
            description=f"Updated term {term.name}",
            changes=changes,
        )

    db.session.commit()
    return term


# ============================== reassign term to a different session =================================

def reassign_term_session(term_id, new_academic_session_id, actor_id):
    term = db.session.get(Term, term_id)
    if term is None:
        return None

    try:
        _check_unique_name(new_academic_session_id, term.name)
        _check_no_overlap(new_academic_session_id, term.start_date, term.end_date)
    except TermValidationError as e:
        abort(400, description=str(e))

    old_session_id = term.academic_session_id
    term.academic_session_id = new_academic_session_id
    term.is_current = False

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.UPDATE,
        resource_type="Term",
        resource_id=term.id,
        description=f"Reassigned term {term.name} to a different academic session",
        changes={"academic_session_id": {"before": old_session_id, "after": new_academic_session_id}},
    )

    db.session.commit()
    return term


# ============================== delete term =================================

def delete_term(term_id, actor_id):
    term = db.session.get(Term, term_id)
    if term is None:
        return False

    if term.attendance_records:
        abort(
            400,
            description=(
                f"Cannot delete term '{term.name}' — it still has "
                f"{len(term.attendance_records)} attendance record(s) referencing it."
            ),
        )

    term_name = term.name
    db.session.delete(term)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="Term",
        resource_id=term_id,
        description=f"Deleted term {term_name}",
    )

    db.session.commit()
    return True


# ============================== activate term =================================

def activate_term(term_id, actor_id):
    term = db.session.get(Term, term_id)
    if term is None:
        return None

    _unset_other_current_terms(term.academic_session_id, exclude_term_id=term.id)
    term.is_current = True

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.UPDATE,
        resource_type="Term",
        resource_id=term.id,
        description=f"Activated term {term.name} as the current term",
    )

    db.session.commit()
    return term