from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.promotion_rule import PromotionRule
from school_app.models.academic_level import AcademicLevel
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ============================ create promotion rule ============================

def create_promotion_rule(data, actor_id):
    from_level = db.session.get(AcademicLevel, data.from_level_id)
    if from_level is None:
        abort(404, description=f"Academic level with ID {data.from_level_id} not found.")

    if data.to_level_id is not None:
        to_level = db.session.get(AcademicLevel, data.to_level_id)
        if to_level is None:
            abort(404, description=f"Academic level with ID {data.to_level_id} not found.")

    if data.is_active:
        _deactivate_existing_active_rule(data.from_level_id)

    rule = PromotionRule(
        name=data.name,
        from_level_id=data.from_level_id,
        to_level_id=data.to_level_id,
        min_average_score=data.min_average_score,
        min_attendance_percentage=data.min_attendance_percentage,
        min_subject_score=data.min_subject_score,
        max_failed_subjects=data.max_failed_subjects,
        requires_admin_approval=data.requires_admin_approval,
        is_active=data.is_active,
    )
    db.session.add(rule)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create promotion rule — check for a duplicate name within this level.")

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="PromotionRule",
        resource_id=rule.id,
        description=f"Created promotion rule {rule.name} for level {from_level.name}",
    )

    db.session.commit()
    return rule


def _deactivate_existing_active_rule(from_level_id):
    """At most one active PromotionRule per from_level_id — enforced here,
    not a DB constraint, same approach as GradingSystem.is_default."""
    db.session.execute(
        db.update(PromotionRule)
        .where(PromotionRule.from_level_id == from_level_id, PromotionRule.is_active.is_(True))
        .values(is_active=False)
    )


# =============================== get all promotion rules =============================

def get_all_promotion_rules(from_level_id=None, include_inactive=False):
    stmt = db.select(PromotionRule)
    if from_level_id is not None:
        stmt = stmt.where(PromotionRule.from_level_id == from_level_id)
    if not include_inactive:
        stmt = stmt.where(PromotionRule.is_active.is_(True))
    return db.session.scalars(stmt).all()


# ============================== get promotion rule ===================================

def get_promotion_rule(rule_id):
    return db.session.get(PromotionRule, rule_id)


def get_active_rule_for_level(level_id):
    """The lookup promotion_service actually uses. Returns the single
    active PromotionRule for a level, or None if the level has no active
    rule configured — callers fall back to hardcoded defaults in that
    case, same pattern as grading_system_service's default-system lookup.
    """
    stmt = db.select(PromotionRule).where(
        PromotionRule.from_level_id == level_id, PromotionRule.is_active.is_(True)
    )
    return db.session.scalars(stmt).first()


# ============================== update promotion rule =================================

def update_promotion_rule(data, rule_id, actor_id):
    rule = db.session.get(PromotionRule, rule_id)
    if rule is None:
        return None

    if data.is_active is True and not rule.is_active:
        _deactivate_existing_active_rule(rule.from_level_id)

    changes = {}
    if data.name is not None and data.name != rule.name:
        changes["name"] = {"before": rule.name, "after": data.name}
        rule.name = data.name
    if data.to_level_id is not None and data.to_level_id != rule.to_level_id:
        changes["to_level_id"] = {"before": rule.to_level_id, "after": data.to_level_id}
        rule.to_level_id = data.to_level_id
    if data.min_average_score is not None and data.min_average_score != rule.min_average_score:
        changes["min_average_score"] = {"before": rule.min_average_score, "after": data.min_average_score}
        rule.min_average_score = data.min_average_score
    if data.min_attendance_percentage is not None and data.min_attendance_percentage != rule.min_attendance_percentage:
        changes["min_attendance_percentage"] = {"before": rule.min_attendance_percentage, "after": data.min_attendance_percentage}
        rule.min_attendance_percentage = data.min_attendance_percentage
    if data.min_subject_score is not None and data.min_subject_score != rule.min_subject_score:
        changes["min_subject_score"] = {"before": rule.min_subject_score, "after": data.min_subject_score}
        rule.min_subject_score = data.min_subject_score
    if data.max_failed_subjects is not None and data.max_failed_subjects != rule.max_failed_subjects:
        changes["max_failed_subjects"] = {"before": rule.max_failed_subjects, "after": data.max_failed_subjects}
        rule.max_failed_subjects = data.max_failed_subjects
    if data.requires_admin_approval is not None and data.requires_admin_approval != rule.requires_admin_approval:
        changes["requires_admin_approval"] = {"before": rule.requires_admin_approval, "after": data.requires_admin_approval}
        rule.requires_admin_approval = data.requires_admin_approval
    if data.is_active is not None and data.is_active != rule.is_active:
        changes["is_active"] = {"before": rule.is_active, "after": data.is_active}
        rule.is_active = data.is_active

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update promotion rule — check for a duplicate name within this level.")

    if changes:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="PromotionRule",
            resource_id=rule.id,
            description=f"Updated promotion rule {rule.name}",
            changes=changes,
        )

    db.session.commit()
    return rule


# ============================== delete promotion rule =================================

def delete_promotion_rule(rule_id, actor_id):
    rule = db.session.get(PromotionRule, rule_id)
    if rule is None:
        return False

    rule_name = rule.name
    db.session.delete(rule)

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DELETE,
        resource_type="PromotionRule",
        resource_id=rule_id,
        description=f"Deleted promotion rule {rule_name}",
    )

    db.session.commit()
    return True