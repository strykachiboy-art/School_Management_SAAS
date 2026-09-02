from datetime import datetime, timezone
from typing import Optional

from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.enums.onboarding import OnboardingStep
from school_app.enums.audit import AuditAction
from school_app.enums.role import Role
from school_app.models.onboarding_progress import OnboardingProgress
from school_app.models.school import School
from school_app.models.academic_stage import AcademicStage
from school_app.models.academic_level import AcademicLevel
from school_app.models.section import Section
from school_app.models.grading_system import GradingSystem
from school_app.models.grading_rule import GradingRule
from school_app.models.promotion_rule import PromotionRule
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.utils.password import hash_password


def _utcnow():
    return datetime.now(timezone.utc)


STEP_ORDER = list(OnboardingStep)

REQUIRED_BEFORE_FINISH = (
    OnboardingStep.SCHOOL_INFO,
    OnboardingStep.LOCALIZATION,
    OnboardingStep.ACADEMIC_STRUCTURE,
    OnboardingStep.GRADING_CONFIG,
    OnboardingStep.PROMOTION_CONFIG,
    OnboardingStep.ADMIN_ACCOUNT,
)


def _next_step(step: OnboardingStep) -> OnboardingStep:
    idx = STEP_ORDER.index(step)
    return STEP_ORDER[idx + 1] if idx + 1 < len(STEP_ORDER) else step


def _mark_step_complete(progress: OnboardingProgress, step: OnboardingStep) -> None:
    """Records a step as done and advances current_step — never regresses
    a step the wizard has already moved past (e.g. going back to edit)."""
    completed = list(progress.completed_steps or [])
    if step.value not in completed:
        completed.append(step.value)
    progress.completed_steps = completed  # reassign — JSON column, in-place append won't be tracked

    if STEP_ORDER.index(step) >= STEP_ORDER.index(progress.current_step):
        progress.current_step = _next_step(step)


# ============================== progress ==============================

def get_or_create_progress(school_id: int) -> OnboardingProgress:
    progress = db.session.execute(
        db.select(OnboardingProgress).filter_by(school_id=school_id)
    ).scalar_one_or_none()

    if progress is not None:
        return progress

    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    progress = OnboardingProgress(school_id=school_id)
    db.session.add(progress)
    db.session.commit()
    return progress


def get_progress(school_id: int) -> Optional[OnboardingProgress]:
    return db.session.execute(
        db.select(OnboardingProgress).filter_by(school_id=school_id)
    ).scalar_one_or_none()


# ============================== step 1: school info ==============================

def submit_school_info(school_id: int, data, actor_id: int) -> OnboardingProgress:
    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    changes = {}
    for field in ("name", "slug", "country"):
        value = getattr(data, field, None)
        if value is not None and value != getattr(school, field):
            changes[field] = {"before": getattr(school, field), "after": value}
            setattr(school, field, value)

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not save school info — slug is already in use.")

    progress = get_or_create_progress(school_id)
    _mark_step_complete(progress, OnboardingStep.SCHOOL_INFO)

    if changes:
        create_audit_log(
            actor_id=actor_id, action=AuditAction.UPDATE, resource_type="School",
            resource_id=school.id, description="Onboarding: updated school info",
            changes=changes, school_id=school_id,
        )

    db.session.commit()
    return progress


# ============================== step 2: localization ==============================

def submit_localization(school_id: int, data, actor_id: int) -> OnboardingProgress:
    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    changes = {}
    for field in ("timezone", "currency", "locale"):
        value = getattr(data, field, None)
        if value is not None and value != getattr(school, field):
            changes[field] = {"before": getattr(school, field), "after": value}
            setattr(school, field, value)

    db.session.flush()

    progress = get_or_create_progress(school_id)
    _mark_step_complete(progress, OnboardingStep.LOCALIZATION)

    if changes:
        create_audit_log(
            actor_id=actor_id, action=AuditAction.UPDATE, resource_type="School",
            resource_id=school.id, description="Onboarding: updated localization settings",
            changes=changes, school_id=school_id,
        )

    db.session.commit()
    return progress


# ============================== step 3: academic structure ==============================

def submit_academic_structure(school_id: int, data, actor_id: int) -> OnboardingProgress:
    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    stage_count = 0

    for stage_order, stage_data in enumerate(data.stages):
        stage_name = stage_data.name.strip()

        stage = db.session.execute(
            db.select(AcademicStage).filter_by(school_id=school_id, name=stage_name)
        ).scalar_one_or_none()

        if stage is None:
            stage = AcademicStage(school_id=school_id, name=stage_name)
            db.session.add(stage)

        stage.code = stage_data.code.strip() if stage_data.code else None
        stage.display_order = stage_data.display_order if stage_data.display_order is not None else stage_order

        try:
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            abort(400, description=f"Could not save academic stage '{stage_name}'.")

        for level_order, level_data in enumerate(stage_data.levels):
            level_name = level_data.name.strip()

            level = db.session.execute(
                db.select(AcademicLevel).filter_by(school_id=school_id, stage_id=stage.id, name=level_name)
            ).scalar_one_or_none()

            if level is None:
                level = AcademicLevel(school_id=school_id, stage_id=stage.id, name=level_name)
                db.session.add(level)

            level.display_order = level_data.display_order if level_data.display_order is not None else level_order

            try:
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                abort(400, description=f"Could not save academic level '{level_name}'.")

            for section_order, section_name in enumerate(level_data.sections):
                section_name = section_name.strip()

                section = db.session.execute(
                    db.select(Section).filter_by(school_id=school_id, level_id=level.id, name=section_name)
                ).scalar_one_or_none()

                if section is None:
                    section = Section(school_id=school_id, level_id=level.id, name=section_name)
                    db.session.add(section)

                section.display_order = section_order

                try:
                    db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    abort(400, description=f"Could not save section '{section_name}'.")

        stage_count += 1

    progress = get_or_create_progress(school_id)
    _mark_step_complete(progress, OnboardingStep.ACADEMIC_STRUCTURE)

    create_audit_log(
        actor_id=actor_id, action=AuditAction.CREATE, resource_type="AcademicStage",
        resource_id=None, description=f"Onboarding: saved {stage_count} academic stage(s)",
        school_id=school_id,
    )

    db.session.commit()
    return progress


# ============================== step 4: grading config ==============================

def submit_grading_config(school_id: int, data, actor_id: int) -> OnboardingProgress:
    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    system = GradingSystem(
        school_id=school_id,
        name=data.name.strip(),
        strategy=data.strategy,
        is_default=True,
    )
    db.session.add(system)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create grading system — duplicate name for this school.")

    for rule_order, rule_data in enumerate(data.rules):
        db.session.add(GradingRule(
            school_id=school_id,
            grading_system_id=system.id,
            grade_name=rule_data.grade_name.strip(),
            min_score=rule_data.min_score,
            max_score=rule_data.max_score,
            grade_point=rule_data.grade_point,
            remark=rule_data.remark,
            display_order=rule_data.display_order if rule_data.display_order is not None else rule_order,
        ))

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create grading rules — duplicate grade name in this system.")

    progress = get_or_create_progress(school_id)
    _mark_step_complete(progress, OnboardingStep.GRADING_CONFIG)

    create_audit_log(
        actor_id=actor_id, action=AuditAction.CREATE, resource_type="GradingSystem",
        resource_id=system.id,
        description=f"Onboarding: created grading system '{system.name}' with {len(data.rules)} rule(s)",
        school_id=school_id,
    )

    db.session.commit()
    return progress


# ============================== step 5: promotion config ==============================

def submit_promotion_config(school_id: int, data, actor_id: int) -> OnboardingProgress:
    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    levels = db.session.scalars(db.select(AcademicLevel).filter_by(school_id=school_id)).all()
    level_by_name = {lvl.name: lvl.id for lvl in levels}

    created = 0
    for rule_data in data.rules:
        from_level_id = level_by_name.get(rule_data.from_level_name)
        if from_level_id is None:
            abort(400, description=f"Unknown academic level '{rule_data.from_level_name}' — create it in the academic structure step first.")

        to_level_id = None
        if rule_data.to_level_name is not None:
            to_level_id = level_by_name.get(rule_data.to_level_name)
            if to_level_id is None:
                abort(400, description=f"Unknown academic level '{rule_data.to_level_name}' — create it in the academic structure step first.")

        db.session.add(PromotionRule(
            school_id=school_id,
            name=rule_data.name.strip(),
            from_level_id=from_level_id,
            to_level_id=to_level_id,
            min_average_score=rule_data.min_average_score,
            min_attendance_percentage=rule_data.min_attendance_percentage,
            min_subject_score=rule_data.min_subject_score,
            max_failed_subjects=rule_data.max_failed_subjects,
            requires_admin_approval=rule_data.requires_admin_approval,
        ))
        created += 1

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create promotion rules — duplicate rule name for this level.")

    progress = get_or_create_progress(school_id)
    _mark_step_complete(progress, OnboardingStep.PROMOTION_CONFIG)

    create_audit_log(
        actor_id=actor_id, action=AuditAction.CREATE, resource_type="PromotionRule",
        resource_id=None, description=f"Onboarding: created {created} promotion rule(s)",
        school_id=school_id,
    )

    db.session.commit()
    return progress


# ============================== step 6: admin account ==============================

def submit_admin_account(school_id: int, data, actor_id: int) -> OnboardingProgress:
    school = db.session.get(School, school_id)
    if school is None:
        abort(404, description="School not found")

    admin = User(
        username=data.username.strip(),
        email=data.email.strip().lower(),
        password=hash_password(data.password),
        role=Role.ADMIN,
        school_id=school_id,
    )
    db.session.add(admin)
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create admin account — username or email already in use.")

    progress = get_or_create_progress(school_id)
    _mark_step_complete(progress, OnboardingStep.ADMIN_ACCOUNT)

    create_audit_log(
        actor_id=actor_id, action=AuditAction.CREATE, resource_type="User",
        resource_id=admin.id, description=f"Onboarding: created admin account '{admin.username}'",
        school_id=school_id,
    )

    db.session.commit()
    return progress


# ============================== finish ==============================

def complete_onboarding(school_id: int, actor_id: int) -> OnboardingProgress:
    progress = get_progress(school_id)
    if progress is None:
        abort(400, description="Onboarding has not been started for this school.")

    completed = set(progress.completed_steps or [])
    missing = [step.value for step in REQUIRED_BEFORE_FINISH if step.value not in completed]
    if missing:
        abort(400, description=f"Cannot complete onboarding — missing step(s): {', '.join(missing)}")

    _mark_step_complete(progress, OnboardingStep.REVIEW)
    progress.is_completed = True
    progress.completed_at = _utcnow()
    progress.current_step = OnboardingStep.DONE

    school = db.session.get(School, school_id)
    if school is not None:
        school.onboarding_completed = True

    create_audit_log(
        actor_id=actor_id, action=AuditAction.UPDATE, resource_type="School",
        resource_id=school_id, description="Onboarding completed", school_id=school_id,
    )

    db.session.commit()
    return progress