from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.grading_system import GradingSystem
from school_app.models.grading_rule import GradingRule
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ create grading system ============================

def create_grading_system(data, actor_id):
    if data.is_default:
        _clear_existing_default(data.school_id)

    system = GradingSystem(
        name=data.name,
        strategy=data.strategy,
        is_default=data.is_default,
        school_id=data.school_id,
    )
    db.session.add(system)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create grading system — check for duplicate name.")

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

    stmt = db.update(GradingSystem).where(GradingSystem.is_default.is_(True))
    if school_id is not None:
        stmt = stmt.where(GradingSystem.school_id == school_id)
    db.session.execute(stmt.values(is_default=False))


# =============================== get all grading systems =============================

def get_all_grading_systems(include_inactive=False):
    stmt = db.select(GradingSystem)
    if not include_inactive:
        stmt = stmt.where(GradingSystem.is_active.is_(True))
    return db.session.scalars(stmt).all()


# ============================== get grading system ===================================

def get_grading_system(system_id):
    return db.session.get(GradingSystem, system_id)


def get_default_grading_system(school_id=None):
    """FIX: used to query is_default=True with no school filter — the
    first is_default=True row found could belong to a different school
    entirely. school_id=None is the explicit single-tenant fallback (same
    documented meaning as _clear_existing_default), not a silent bug.
    """
    stmt = db.select(GradingSystem).where(GradingSystem.is_default.is_(True), GradingSystem.is_active.is_(True))
    if school_id is not None:
        stmt = stmt.where(GradingSystem.school_id == school_id)
    return db.session.scalars(stmt).first()


# ============================== update grading system =================================

def update_grading_system(data, system_id, actor_id):
    system = db.session.get(GradingSystem, system_id)
    if system is None:
        return None

    if data.is_default is True and not system.is_default:
        _clear_existing_default(system.school_id)

    changes = {}
    if data.name is not None and data.name != system.name:
        changes["name"] = {"before": system.name, "after": data.name}
        system.name = data.name
    if data.strategy is not None and data.strategy != system.strategy:
        changes["strategy"] = {"before": system.strategy, "after": data.strategy}
        system.strategy = data.strategy
    if data.is_default is not None and data.is_default != system.is_default:
        changes["is_default"] = {"before": system.is_default, "after": data.is_default}
        system.is_default = data.is_default
    if data.is_active is not None and data.is_active != system.is_active:
        changes["is_active"] = {"before": system.is_active, "after": data.is_active}
        system.is_active = data.is_active

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update grading system — check for duplicate name.")

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


# ============================== delete grading system =================================

def delete_grading_system(system_id, actor_id):
    system = db.session.get(GradingSystem, system_id)
    if system is None:
        return False

    if system.is_default:
        abort(400, description="Cannot delete the default grading system — set another system as default first.")

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



# ============================ create grading rule ============================

def create_grading_rule(data, actor_id):
    system = db.session.get(GradingSystem, data.grading_system_id)

    if system is None:
        abort(
            404,
            description=f"Grading system with ID {data.grading_system_id} not found.",
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
            description="Could not create grading rule — check for a duplicate grade name within this system.",
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


# ============================== update grading rule =================================

def update_grading_rule(data, rule_id, actor_id):
    rule = db.session.get(GradingRule, rule_id)
    if rule is None:
        return None

    changes = {}
    if data.grade_name is not None and data.grade_name != rule.grade_name:
        changes["grade_name"] = {"before": rule.grade_name, "after": data.grade_name}
        rule.grade_name = data.grade_name
    if data.min_score is not None and data.min_score != rule.min_score:
        changes["min_score"] = {"before": rule.min_score, "after": data.min_score}
        rule.min_score = data.min_score
    if data.max_score is not None and data.max_score != rule.max_score:
        changes["max_score"] = {"before": rule.max_score, "after": data.max_score}
        rule.max_score = data.max_score
    if data.grade_point is not None and data.grade_point != rule.grade_point:
        changes["grade_point"] = {"before": rule.grade_point, "after": data.grade_point}
        rule.grade_point = data.grade_point
    if data.remark is not None and data.remark != rule.remark:
        changes["remark"] = {"before": rule.remark, "after": data.remark}
        rule.remark = data.remark
    if data.display_order is not None and data.display_order != rule.display_order:
        changes["display_order"] = {"before": rule.display_order, "after": data.display_order}
        rule.display_order = data.display_order

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update grading rule — check for a duplicate grade name within this system.")

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


# ============================== delete grading rule =================================

def delete_grading_rule(rule_id, actor_id):
    rule = db.session.get(GradingRule, rule_id)
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


# ============================== lookup: score -> (grade, remark) =================================

def resolve_grade_for_score(score, grading_system_id=None, school_id=None):
    
    if grading_system_id is not None:
        system = db.session.get(GradingSystem, grading_system_id)
    else:
        system = get_default_grading_system(school_id=school_id)

    if system is None:
        return None, None, False

    stmt = (
        db.select(GradingRule)
        .where(GradingRule.grading_system_id == system.id)
        .order_by(GradingRule.min_score.desc())
    )
    rules = db.session.scalars(stmt).all()

    for rule in rules:
        if score >= rule.min_score and (rule.max_score is None or score <= rule.max_score):
            return rule.grade_name, rule.remark, True

    return None, None, True