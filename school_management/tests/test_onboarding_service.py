import pytest
from werkzeug.exceptions import HTTPException

from school_app.enums.grading import GradingStrategy
from school_app.enums.onboarding import OnboardingStep
from school_app.extensions import db
from school_app.models.academic_level import AcademicLevel
from school_app.models.academic_stage import AcademicStage
from school_app.models.grading_rule import GradingRule
from school_app.models.grading_system import GradingSystem
from school_app.models.onboarding_progress import OnboardingProgress
from school_app.models.promotion_rule import PromotionRule
from school_app.models.school import School
from school_app.models.section import Section
from school_app.models.user import User
from school_app.modules.onboarding.requests.onboarding_request import (
    AcademicStructureStepRequest,
    AdminAccountStepRequest,
    GradingConfigStepRequest,
    LocalizationStepRequest,
    PromotionConfigStepRequest,
    SchoolInfoStepRequest,
)
from school_app.modules.onboarding.services.onboarding_service import (
    complete_onboarding,
    get_or_create_progress,
    get_progress,
    submit_academic_structure,
    submit_admin_account,
    submit_grading_config,
    submit_localization,
    submit_promotion_config,
    submit_school_info,
)


# ============================================================================
# HELPERS
# ============================================================================

def assert_http_error(exc_info, status_code):
    assert exc_info.value.code == status_code


def academic_structure_payload():
    return AcademicStructureStepRequest(
        stages=[
            {
                "name": "Primary",
                "code": "P",
                "display_order": 1,
                "levels": [
                    {
                        "name": "Grade 1",
                        "display_order": 0,
                        "sections": ["A", "B"],
                    },
                    {
                        "name": "Grade 2",
                        "display_order": 1,
                        "sections": ["A", "B"],
                    },
                ],
            }
        ]
    )


def grading_config_payload(name="Standard Grading"):
    return GradingConfigStepRequest(
        name=name,
        strategy=GradingStrategy.LETTER_GRADE,
        rules=[
            {
                "grade_name": "A",
                "min_score": 70,
                "max_score": 100,
                "grade_point": 4.0,
                "remark": "Excellent",
                "display_order": 0,
            },
            {
                "grade_name": "B",
                "min_score": 60,
                "max_score": 69,
                "grade_point": 3.0,
                "remark": "Very Good",
                "display_order": 1,
            },
        ],
    )


def promotion_config_payload():
    return PromotionConfigStepRequest(
        rules=[
            {
                "name": "Grade 1 to Grade 2",
                "from_level_name": "Grade 1",
                "to_level_name": "Grade 2",
                "min_average_score": 50,
                "min_attendance_percentage": 75,
                "max_failed_subjects": 2,
                "requires_admin_approval": True,
            }
        ]
    )


# ============================================================================
# GET / CREATE PROGRESS
# ============================================================================

def test_get_or_create_progress_creates_progress(
    app,
    school,
):
    with app.app_context():
        progress = get_or_create_progress(school.id)

        assert progress.id is not None
        assert progress.school_id == school.id
        assert progress.current_step == OnboardingStep.SCHOOL_INFO
        assert progress.completed_steps == []
        assert progress.is_completed is False

        stored = get_progress(school.id)

        assert stored is not None
        assert stored.id == progress.id


def test_get_or_create_progress_returns_existing_progress(
    app,
    school,
):
    with app.app_context():
        first = get_or_create_progress(school.id)
        second = get_or_create_progress(school.id)

        assert first.id == second.id

        count = db.session.scalar(
            db.select(db.func.count(OnboardingProgress.id))
            .where(
                OnboardingProgress.school_id == school.id
            )
        )

        assert count == 1


def test_get_or_create_progress_rejects_unknown_school(
    app,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            get_or_create_progress(999999)

        assert_http_error(exc_info, 404)


def test_get_progress_returns_none_when_not_started(
    app,
    school,
):
    with app.app_context():
        assert get_progress(school.id) is None


# ============================================================================
# SCHOOL INFO
# ============================================================================

def test_submit_school_info_updates_school_and_progress(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = SchoolInfoStepRequest(
            name="Updated School",
            slug="updated-school",
            country="Nigeria",
        )

        progress = submit_school_info(
            school.id,
            payload,
            admin_actor_id,
        )

        # The service commits its own transaction, so the fixture instance
        # may no longer be attached to the current session. Query it again.
        updated_school = db.session.get(School, school.id)

        assert updated_school is not None
        assert updated_school.name == "Updated School"
        assert updated_school.slug == "updated-school"
        assert updated_school.country == "Nigeria"

        assert (
            OnboardingStep.SCHOOL_INFO.value
            in progress.completed_steps
        )
        assert progress.current_step == OnboardingStep.LOCALIZATION


def test_submit_school_info_accepts_partial_payload(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        original_name = school.name
        original_slug = school.slug

        payload = SchoolInfoStepRequest(
            country="Nigeria",
        )

        progress = submit_school_info(
            school.id,
            payload,
            admin_actor_id,
        )

        updated_school = db.session.get(School, school.id)

        assert updated_school is not None
        assert updated_school.name == original_name
        assert updated_school.slug == original_slug
        assert updated_school.country == "Nigeria"

        assert (
            OnboardingStep.SCHOOL_INFO.value
            in progress.completed_steps
        )


def test_submit_school_info_rejects_unknown_school(
    app,
    admin_actor_id,
):
    with app.app_context():
        payload = SchoolInfoStepRequest(
            name="Updated School",
        )

        with pytest.raises(HTTPException) as exc_info:
            submit_school_info(
                999999,
                payload,
                admin_actor_id,
            )

        assert_http_error(exc_info, 404)


# ============================================================================
# LOCALIZATION
# ============================================================================

def test_submit_localization_updates_school_and_progress(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = LocalizationStepRequest(
            timezone="Africa/Lagos",
            currency="NGN",
            locale="en-NG",
        )

        progress = submit_localization(
            school.id,
            payload,
            admin_actor_id,
        )

        updated_school = db.session.get(School, school.id)

        assert updated_school is not None
        assert updated_school.timezone == "Africa/Lagos"
        assert updated_school.currency == "NGN"
        assert updated_school.locale == "en-NG"

        assert (
            OnboardingStep.LOCALIZATION.value
            in progress.completed_steps
        )

        # Completing LOCALIZATION advances current_step to the next
        # step in STEP_ORDER.
        assert progress.current_step == OnboardingStep.ACADEMIC_STRUCTURE


def test_submit_localization_rejects_unknown_school(
    app,
    admin_actor_id,
):
    with app.app_context():
        payload = LocalizationStepRequest(
            timezone="Africa/Lagos",
            currency="NGN",
            locale="en-NG",
        )

        with pytest.raises(HTTPException) as exc_info:
            submit_localization(
                999999,
                payload,
                admin_actor_id,
            )

        assert_http_error(exc_info, 404)


# ============================================================================
# ACADEMIC STRUCTURE
# ============================================================================

def test_submit_academic_structure_creates_stage_levels_sections(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = academic_structure_payload()

        progress = submit_academic_structure(
            school.id,
            payload,
            admin_actor_id,
        )

        stages = db.session.scalars(
            db.select(AcademicStage).filter_by(
                school_id=school.id
            )
        ).all()

        levels = db.session.scalars(
            db.select(AcademicLevel).filter_by(
                school_id=school.id
            )
        ).all()

        sections = db.session.scalars(
            db.select(Section).filter_by(
                school_id=school.id
            )
        ).all()

        assert len(stages) == 1
        assert len(levels) == 2
        assert len(sections) == 4

        assert stages[0].name == "Primary"
        assert stages[0].code == "P"
        assert stages[0].display_order == 1

        level_names = {level.name for level in levels}

        assert level_names == {
            "Grade 1",
            "Grade 2",
        }

        section_names = [section.name for section in sections]

        assert section_names.count("A") == 2
        assert section_names.count("B") == 2

        assert (
            OnboardingStep.ACADEMIC_STRUCTURE.value
            in progress.completed_steps
        )

        assert progress.current_step == OnboardingStep.GRADING_CONFIG


def test_submit_academic_structure_is_idempotent(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = AcademicStructureStepRequest(
            stages=[
                {
                    "name": "Primary",
                    "code": "P",
                    "display_order": 1,
                    "levels": [
                        {
                            "name": "Grade 1",
                            "display_order": 0,
                            "sections": ["A", "B"],
                        }
                    ],
                }
            ]
        )

        first = submit_academic_structure(
            school.id,
            payload,
            admin_actor_id,
        )

        second = submit_academic_structure(
            school.id,
            payload,
            admin_actor_id,
        )

        stages = db.session.scalars(
            db.select(AcademicStage).filter_by(
                school_id=school.id
            )
        ).all()

        levels = db.session.scalars(
            db.select(AcademicLevel).filter_by(
                school_id=school.id
            )
        ).all()

        sections = db.session.scalars(
            db.select(Section).filter_by(
                school_id=school.id
            )
        ).all()

        assert len(stages) == 1
        assert len(levels) == 1
        assert len(sections) == 2

        assert first.completed_steps == second.completed_steps

        assert (
            OnboardingStep.ACADEMIC_STRUCTURE.value
            in second.completed_steps
        )

        assert second.current_step == OnboardingStep.GRADING_CONFIG


def test_submit_academic_structure_updates_existing_records(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        first_payload = AcademicStructureStepRequest(
            stages=[
                {
                    "name": "Primary",
                    "code": "P",
                    "display_order": 1,
                    "levels": [
                        {
                            "name": "Grade 1",
                            "display_order": 0,
                            "sections": ["A"],
                        }
                    ],
                }
            ]
        )

        submit_academic_structure(
            school.id,
            first_payload,
            admin_actor_id,
        )

        second_payload = AcademicStructureStepRequest(
            stages=[
                {
                    "name": "Primary",
                    "code": "PRIMARY",
                    "display_order": 5,
                    "levels": [
                        {
                            "name": "Grade 1",
                            "display_order": 10,
                            "sections": ["A", "B"],
                        }
                    ],
                }
            ]
        )

        submit_academic_structure(
            school.id,
            second_payload,
            admin_actor_id,
        )

        stage = db.session.scalar(
            db.select(AcademicStage).filter_by(
                school_id=school.id,
                name="Primary",
            )
        )

        level = db.session.scalar(
            db.select(AcademicLevel).filter_by(
                school_id=school.id,
                name="Grade 1",
            )
        )

        sections = db.session.scalars(
            db.select(Section).filter_by(
                school_id=school.id,
                level_id=level.id,
            )
        ).all()

        assert stage is not None
        assert level is not None

        assert stage.code == "PRIMARY"
        assert stage.display_order == 5
        assert level.display_order == 10
        assert {section.name for section in sections} == {"A", "B"}


def test_submit_academic_structure_rejects_unknown_school(
    app,
    admin_actor_id,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            submit_academic_structure(
                999999,
                academic_structure_payload(),
                admin_actor_id,
            )

        assert_http_error(exc_info, 404)


# ============================================================================
# GRADING CONFIG
# ============================================================================

def test_submit_grading_config_creates_system_and_rules(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = grading_config_payload()

        progress = submit_grading_config(
            school.id,
            payload,
            admin_actor_id,
        )

        system = db.session.scalar(
            db.select(GradingSystem).filter_by(
                school_id=school.id,
                name="Standard Grading",
            )
        )

        assert system is not None
        assert system.is_default is True
        assert system.strategy == GradingStrategy.LETTER_GRADE

        rules = db.session.scalars(
            db.select(GradingRule).filter_by(
                grading_system_id=system.id
            )
        ).all()

        assert len(rules) == 2

        assert {rule.grade_name for rule in rules} == {"A", "B"}

        grade_a = next(
            rule for rule in rules
            if rule.grade_name == "A"
        )

        grade_b = next(
            rule for rule in rules
            if rule.grade_name == "B"
        )

        assert grade_a.min_score == 70
        assert grade_a.max_score == 100
        assert grade_a.grade_point == 4.0
        assert grade_a.remark == "Excellent"

        assert grade_b.min_score == 60
        assert grade_b.max_score == 69
        assert grade_b.grade_point == 3.0
        assert grade_b.remark == "Very Good"

        assert (
            OnboardingStep.GRADING_CONFIG.value
            in progress.completed_steps
        )

        assert progress.current_step == OnboardingStep.PROMOTION_CONFIG


def test_submit_grading_config_rejects_unknown_school(
    app,
    admin_actor_id,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            submit_grading_config(
                999999,
                grading_config_payload(),
                admin_actor_id,
            )

        assert_http_error(exc_info, 404)


def test_submit_grading_config_creates_custom_named_system(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = grading_config_payload(
            name="WAEC Grading"
        )

        submit_grading_config(
            school.id,
            payload,
            admin_actor_id,
        )

        system = db.session.scalar(
            db.select(GradingSystem).filter_by(
                school_id=school.id,
                name="WAEC Grading",
            )
        )

        assert system is not None


# ============================================================================
# PROMOTION CONFIG
# ============================================================================

def test_submit_promotion_config_creates_rules(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        submit_academic_structure(
            school.id,
            academic_structure_payload(),
            admin_actor_id,
        )

        payload = promotion_config_payload()

        progress = submit_promotion_config(
            school.id,
            payload,
            admin_actor_id,
        )

        rules = db.session.scalars(
            db.select(PromotionRule).filter_by(
                school_id=school.id
            )
        ).all()

        assert len(rules) == 1

        rule = rules[0]

        assert rule.name == "Grade 1 to Grade 2"

        from_level = db.session.get(
            AcademicLevel,
            rule.from_level_id,
        )

        to_level = db.session.get(
            AcademicLevel,
            rule.to_level_id,
        )

        assert from_level is not None
        assert to_level is not None

        assert from_level.name == "Grade 1"
        assert to_level.name == "Grade 2"

        assert rule.min_average_score == 50
        assert rule.min_attendance_percentage == 75
        assert rule.max_failed_subjects == 2
        assert rule.requires_admin_approval is True

        assert (
            OnboardingStep.PROMOTION_CONFIG.value
            in progress.completed_steps
        )

        assert progress.current_step == OnboardingStep.ADMIN_ACCOUNT


def test_submit_promotion_config_accepts_empty_rules(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = PromotionConfigStepRequest(
            rules=[]
        )

        progress = submit_promotion_config(
            school.id,
            payload,
            admin_actor_id,
        )

        rules = db.session.scalars(
            db.select(PromotionRule).filter_by(
                school_id=school.id
            )
        ).all()

        assert rules == []

        assert (
            OnboardingStep.PROMOTION_CONFIG.value
            in progress.completed_steps
        )

        assert progress.current_step == OnboardingStep.ADMIN_ACCOUNT


def test_submit_promotion_config_rejects_unknown_from_level(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = PromotionConfigStepRequest(
            rules=[
                {
                    "name": "Invalid Promotion",
                    "from_level_name": "Does Not Exist",
                    "to_level_name": None,
                }
            ]
        )

        with pytest.raises(HTTPException) as exc_info:
            submit_promotion_config(
                school.id,
                payload,
                admin_actor_id,
            )

        assert_http_error(exc_info, 400)


def test_submit_promotion_config_rejects_unknown_to_level(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        submit_academic_structure(
            school.id,
            academic_structure_payload(),
            admin_actor_id,
        )

        payload = PromotionConfigStepRequest(
            rules=[
                {
                    "name": "Invalid Promotion",
                    "from_level_name": "Grade 1",
                    "to_level_name": "Does Not Exist",
                }
            ]
        )

        with pytest.raises(HTTPException) as exc_info:
            submit_promotion_config(
                school.id,
                payload,
                admin_actor_id,
            )

        assert_http_error(exc_info, 400)


# ============================================================================
# ADMIN ACCOUNT
# ============================================================================

def test_submit_admin_account_creates_admin(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = AdminAccountStepRequest(
            username="newschooladmin",
            email="newadmin@example.com",
            password="StrongPassword123!",
        )

        progress = submit_admin_account(
            school.id,
            payload,
            admin_actor_id,
        )

        admin = db.session.scalar(
            db.select(User).filter_by(
                username="newschooladmin"
            )
        )

        assert admin is not None
        assert admin.email == "newadmin@example.com"
        assert admin.school_id == school.id
        assert admin.role.value == "admin" if hasattr(admin.role, "value") else admin.role == "admin"

        # The service hashes the password.
        assert admin.password != "StrongPassword123!"

        assert (
            OnboardingStep.ADMIN_ACCOUNT.value
            in progress.completed_steps
        )

        assert progress.current_step == OnboardingStep.REVIEW


def test_submit_admin_account_normalizes_username_and_email(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        payload = AdminAccountStepRequest(
            username="  schooladmin  ",
            email="  ADMIN@Example.COM  ",
            password="StrongPassword123!",
        )

        progress = submit_admin_account(
            school.id,
            payload,
            admin_actor_id,
        )

        admin = db.session.scalar(
            db.select(User).filter_by(
                username="schooladmin"
            )
        )

        assert admin is not None
        assert admin.email == "admin@example.com"

        assert (
            OnboardingStep.ADMIN_ACCOUNT.value
            in progress.completed_steps
        )


def test_submit_admin_account_rejects_unknown_school(
    app,
    admin_actor_id,
):
    with app.app_context():
        payload = AdminAccountStepRequest(
            username="newschooladmin",
            email="newadmin@example.com",
            password="StrongPassword123!",
        )

        with pytest.raises(HTTPException) as exc_info:
            submit_admin_account(
                999999,
                payload,
                admin_actor_id,
            )

        assert_http_error(exc_info, 404)


# ============================================================================
# COMPLETE ONBOARDING
# ============================================================================

def test_complete_onboarding_rejects_when_progress_missing(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            complete_onboarding(
                school.id,
                admin_actor_id,
            )

        assert_http_error(exc_info, 400)


def test_complete_onboarding_rejects_missing_required_steps(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        get_or_create_progress(school.id)

        with pytest.raises(HTTPException) as exc_info:
            complete_onboarding(
                school.id,
                admin_actor_id,
            )

        assert_http_error(exc_info, 400)


def test_complete_onboarding_success(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        # 1. School info
        submit_school_info(
            school.id,
            SchoolInfoStepRequest(
                name="Completed School",
                slug="completed-school",
                country="Nigeria",
            ),
            admin_actor_id,
        )

        # 2. Localization
        submit_localization(
            school.id,
            LocalizationStepRequest(
                timezone="Africa/Lagos",
                currency="NGN",
                locale="en-NG",
            ),
            admin_actor_id,
        )

        # 3. Academic structure
        submit_academic_structure(
            school.id,
            academic_structure_payload(),
            admin_actor_id,
        )

        # 4. Grading config
        submit_grading_config(
            school.id,
            grading_config_payload(),
            admin_actor_id,
        )

        # 5. Promotion config
        submit_promotion_config(
            school.id,
            promotion_config_payload(),
            admin_actor_id,
        )

        # 6. Admin account
        submit_admin_account(
            school.id,
            AdminAccountStepRequest(
                username="finaladmin",
                email="finaladmin@example.com",
                password="StrongPassword123!",
            ),
            admin_actor_id,
        )

        progress = complete_onboarding(
            school.id,
            admin_actor_id,
        )

        assert progress.is_completed is True
        assert progress.current_step == OnboardingStep.DONE
        assert progress.completed_at is not None

        required_steps = {
            step.value
            for step in (
                OnboardingStep.SCHOOL_INFO,
                OnboardingStep.LOCALIZATION,
                OnboardingStep.ACADEMIC_STRUCTURE,
                OnboardingStep.GRADING_CONFIG,
                OnboardingStep.PROMOTION_CONFIG,
                OnboardingStep.ADMIN_ACCOUNT,
            )
        }

        assert required_steps.issubset(
            set(progress.completed_steps)
        )

        assert (
            OnboardingStep.REVIEW.value
            in progress.completed_steps
        )

        # Re-query because the service commits its transaction.
        updated_school = db.session.get(School, school.id)

        assert updated_school is not None
        assert updated_school.onboarding_completed is True


def test_complete_onboarding_sets_done_even_after_review(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        progress = get_or_create_progress(school.id)

        progress.completed_steps = [
            step.value
            for step in (
                OnboardingStep.SCHOOL_INFO,
                OnboardingStep.LOCALIZATION,
                OnboardingStep.ACADEMIC_STRUCTURE,
                OnboardingStep.GRADING_CONFIG,
                OnboardingStep.PROMOTION_CONFIG,
                OnboardingStep.ADMIN_ACCOUNT,
            )
        ]

        db.session.commit()

        completed = complete_onboarding(
            school.id,
            admin_actor_id,
        )

        assert completed.is_completed is True
        assert completed.current_step == OnboardingStep.DONE

        assert (
            OnboardingStep.REVIEW.value
            in completed.completed_steps
        )