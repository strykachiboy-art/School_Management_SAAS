from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.grading_system import GradingSystem
from school_app.models.grading_rule import GradingRule
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================================================================
# GRADING SYSTEM
# ============================================================================

def create_grading_system(data, actor_id):
    """
    Create a new grading system.

    If the new system is marked as default, any existing default system
    for the same school is cleared first.
    """
    if data.is_default:
        _clear_existing_default(data.school_id)

    system = GradingSystem(
          name=data.name,
          strategy=data.strategy,
          is_default=data.is_default,
          school_id=data.school_id,
          is_active=getattr(data, "is_active", True),
         )

    db.session.add(system)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description=(
                "Could not create grading system — "
                "check for duplicate name."
            ),
        )

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="GradingSystem",
        resource_id=system.id,
        description=f"Created grading system {system.name}",
    )

    db.session.commit()
    return system


def _clear_existing_default(school_id=None):
    """
    Remove the default flag from existing grading systems.

    When school_id is provided, only systems belonging to that school
    are affected.
    """
    stmt = db.update(GradingSystem).where(
        GradingSystem.is_default.is_(True)
    )

    if school_id is not None:
        stmt = stmt.where(
            GradingSystem.school_id == school_id
        )

    db.session.execute(
        stmt.values(is_default=False)
    )


def get_all_grading_systems(include_inactive=False):
    stmt = db.select(GradingSystem)

    if not include_inactive:
        stmt = stmt.where(
            GradingSystem.is_active.is_(True)
        )

    stmt = stmt.order_by(GradingSystem.name.asc())

    return db.session.scalars(stmt).all()



def get_grading_system(system_id):
    """Return a grading system by ID, or None if it does not exist."""
    return db.session.get(GradingSystem, system_id)


def get_default_grading_system(school_id=None):
    """
    Return the active default grading system.

    If school_id is provided, the lookup is restricted to that school.
    """
    stmt = (
        db.select(GradingSystem)
        .where(
            GradingSystem.is_default.is_(True),
            GradingSystem.is_active.is_(True),
        )
    )

    if school_id is not None:
        stmt = stmt.where(
            GradingSystem.school_id == school_id
        )

    return db.session.scalars(stmt).first()


def update_grading_system(data, system_id, actor_id):
    """
    Update an existing grading system.

    If the system is being promoted to default, any other default system
    belonging to the same school is cleared first.
    """
    system = db.session.get(GradingSystem, system_id)

    if system is None:
        return None

    # If changing this system to default, clear the old default first.
    if data.is_default is True and not system.is_default:
        _clear_existing_default(system.school_id)

    changes = {}

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------
    if (
        data.name is not None
        and data.name != system.name
    ):
        changes["name"] = {
            "before": system.name,
            "after": data.name,
        }

        system.name = data.name

    # ------------------------------------------------------------------
    # Strategy
    # ------------------------------------------------------------------
    if (
        data.strategy is not None
        and data.strategy != system.strategy
    ):
        changes["strategy"] = {
            "before": system.strategy,
            "after": data.strategy,
        }

        system.strategy = data.strategy

    # ------------------------------------------------------------------
    # Default
    # ------------------------------------------------------------------
    if (
        data.is_default is not None
        and data.is_default != system.is_default
    ):
        changes["is_default"] = {
            "before": system.is_default,
            "after": data.is_default,
        }

        system.is_default = data.is_default

    # ------------------------------------------------------------------
    # Active status
    # ------------------------------------------------------------------
    if (
        data.is_active is not None
        and data.is_active != system.is_active
    ):
        changes["is_active"] = {
            "before": system.is_active,
            "after": data.is_active,
        }

        system.is_active = data.is_active

    try:
        db.session.flush()

    except IntegrityError:
        db.session.rollback()

        abort(
            400,
            description=(
                "Could not update grading system — "
                "check for duplicate name."
            ),
        )

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="GradingSystem",
            resource_id=system.id,
            description=f"Updated grading system {system.name}",
            changes=changes,
        )

    db.session.commit()
    return system


def delete_grading_system(system_id, actor_id):
    """
    Permanently delete a grading system.

    The default grading system cannot be deleted until another system
    has been made default.
    """
    system = db.session.get(
        GradingSystem,
        system_id,
    )

    if system is None:
        return False

    if system.is_default:
        abort(
            400,
            description=(
                "Cannot delete the default grading system — "
                "set another system as default first."
            ),
        )

    system_name = system.name

    db.session.delete(system)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="GradingSystem",
        resource_id=system_id,
        description=f"Deleted grading system {system_name}",
    )

    db.session.commit()
    return True


# ============================================================================
# GRADING RULE
# ============================================================================

def create_grading_rule(data, actor_id):
    """
    Create a grading rule belonging to an existing grading system.
    """
    system = db.session.get(
        GradingSystem,
        data.grading_system_id,
    )

    if system is None:
        abort(
            404,
            description=(
                f"Grading system with ID "
                f"{data.grading_system_id} not found."
            ),
        )

    rule = GradingRule(
        school_id=system.school_id,
        grading_system_id=data.grading_system_id,
        grade_name=data.grade_name,
        min_score=data.min_score,
        max_score=data.max_score,
        grade_point=data.grade_point,
        remark=data.remark,
        display_order=data.display_order,
    )

    db.session.add(rule)

    try:
        db.session.flush()

    except IntegrityError:
        db.session.rollback()

        abort(
            400,
            description=(
                "Could not create grading rule — "
                "check for a duplicate grade name within this system."
            ),
        )

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="GradingRule",
        resource_id=rule.id,
        description=f"Created grading rule '{rule.grade_name}'",
    )

    db.session.commit()
    return rule


def update_grading_rule(data, rule_id, actor_id):
    """
    Update an existing grading rule.
    """
    rule = db.session.get(
        GradingRule,
        rule_id,
    )

    if rule is None:
        return None

    changes = {}

    # ------------------------------------------------------------------
    # Grade name
    # ------------------------------------------------------------------
    if (
        data.grade_name is not None
        and data.grade_name != rule.grade_name
    ):
        changes["grade_name"] = {
            "before": rule.grade_name,
            "after": data.grade_name,
        }

        rule.grade_name = data.grade_name

    # ------------------------------------------------------------------
    # Minimum score
    # ------------------------------------------------------------------
    if (
        data.min_score is not None
        and data.min_score != rule.min_score
    ):
        changes["min_score"] = {
            "before": rule.min_score,
            "after": data.min_score,
        }

        rule.min_score = data.min_score

    # ------------------------------------------------------------------
    # Maximum score
    # ------------------------------------------------------------------
    if (
        data.max_score is not None
        and data.max_score != rule.max_score
    ):
        changes["max_score"] = {
            "before": rule.max_score,
            "after": data.max_score,
        }

        rule.max_score = data.max_score

    # ------------------------------------------------------------------
    # Grade point
    # ------------------------------------------------------------------
    if (
        data.grade_point is not None
        and data.grade_point != rule.grade_point
    ):
        changes["grade_point"] = {
            "before": rule.grade_point,
            "after": data.grade_point,
        }

        rule.grade_point = data.grade_point

    # ------------------------------------------------------------------
    # Remark
    # ------------------------------------------------------------------
    if (
        data.remark is not None
        and data.remark != rule.remark
    ):
        changes["remark"] = {
            "before": rule.remark,
            "after": data.remark,
        }

        rule.remark = data.remark

    # ------------------------------------------------------------------
    # Display order
    # ------------------------------------------------------------------
    if (
        data.display_order is not None
        and data.display_order != rule.display_order
    ):
        changes["display_order"] = {
            "before": rule.display_order,
            "after": data.display_order,
        }

        rule.display_order = data.display_order

    try:
        db.session.flush()

    except IntegrityError:
        db.session.rollback()

        abort(
            400,
            description=(
                "Could not update grading rule — "
                "check for a duplicate grade name within this system."
            ),
        )

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="GradingRule",
            resource_id=rule.id,
            description=f"Updated grading rule {rule.grade_name}",
            changes=changes,
        )

    db.session.commit()
    return rule


def delete_grading_rule(rule_id, actor_id):
    """
    Permanently delete a grading rule.
    """
    rule = db.session.get(
        GradingRule,
        rule_id,
    )

    if rule is None:
        return False

    rule_name = rule.grade_name

    db.session.delete(rule)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="GradingRule",
        resource_id=rule_id,
        description=f"Deleted grading rule {rule_name}",
    )

    db.session.commit()
    return True


# ============================================================================
# SCORE LOOKUP
# ============================================================================

def resolve_grade_for_score(
    score,
    grading_system_id=None,
    school_id=None,
):
    """
    Resolve a numeric score into:

        (grade_name, remark, found)

    If no grading system exists:
        (None, None, False)

    If a grading system exists but no rule matches:
        (None, None, True)
    """
    if grading_system_id is not None:
        system = db.session.get(
            GradingSystem,
            grading_system_id,
        )
    else:
        system = get_default_grading_system(
            school_id=school_id,
        )

    if system is None:
        return None, None, False

    stmt = (
        db.select(GradingRule)
        .where(
            GradingRule.grading_system_id == system.id
        )
        .order_by(
            GradingRule.min_score.desc()
        )
    )

    rules = db.session.scalars(stmt).all()

    for rule in rules:
        if (
            score >= rule.min_score
            and (
                rule.max_score is None
                or score <= rule.max_score
            )
        ):
            return (
                rule.grade_name,
                rule.remark,
                True,
            )

    return None, None, True
