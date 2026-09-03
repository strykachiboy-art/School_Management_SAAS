import pytest
from werkzeug.exceptions import HTTPException

from school_app.enums.grading import GradingStrategy
from school_app.enums.onboarding import OnboardingStep
from school_app.enums.settings import NotificationChannel
from school_app.enums.notification import NotificationType
from school_app.enums.role import Role
from school_app.extensions import db as _db
from school_app.models.academic_level import AcademicLevel
from school_app.models.academic_stage import AcademicStage
from school_app.models.grading_rule import GradingRule
from school_app.models.grading_system import GradingSystem
from school_app.models.school import School
from school_app.models.school_settings import SchoolSettings
from school_app.modules.settings.services import settings_service


# ======================================================================
# HELPERS
# ======================================================================


def _get_audit_logs_for_settings(settings_id):
    """
    Return audit logs associated with a SchoolSettings record.

    The exact audit model/schema in the project may vary, so this helper
    intentionally uses the application's audit service/model only when
    available through the database relationships/query API.
    """
    from school_app.models.audit_log import AuditLog

    return _db.session.execute(
        _db.select(AuditLog)
        .where(
            AuditLog.resource_type == "SchoolSettings",
            AuditLog.resource_id == settings_id,
        )
        .order_by(AuditLog.id.asc())
    ).scalars().all()


# ======================================================================
# GET / CREATE SETTINGS
# ======================================================================


def test_get_or_create_settings_creates_settings_for_existing_school(
    app,
    school,
):
    with app.app_context():
        existing = _db.session.execute(
            _db.select(SchoolSettings).filter_by(
                school_id=school.id
            )
        ).scalar_one_or_none()

        assert existing is None

        settings = settings_service.get_or_create_settings(
            school.id
        )

        assert settings is not None
        assert settings.school_id == school.id
        assert settings.id is not None

        persisted = _db.session.execute(
            _db.select(SchoolSettings).filter_by(
                school_id=school.id
            )
        ).scalar_one()

        assert persisted.id == settings.id


def test_get_or_create_settings_returns_existing_settings(
    app,
    school_settings,
):
    with app.app_context():
        settings = settings_service.get_or_create_settings(
            school_settings.school_id
        )

        assert settings.id == school_settings.id
        assert settings.school_id == school_settings.school_id


def test_get_or_create_settings_fails_for_missing_school(
    app,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            settings_service.get_or_create_settings(999999)

        assert exc_info.value.code == 404


# ======================================================================
# BRANDING SETTINGS
# ======================================================================


def test_update_branding_updates_only_supplied_fields(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            motto="Old Motto",
            address="Old Address",
            phone="08000000000",
        )

        _db.session.add(settings)
        _db.session.commit()

        class BrandingData:
            def model_dump(self, exclude_unset=False):
                return {
                    "motto": "New Motto",
                    "address": "New Address",
                }

        updated = settings_service.update_branding(
            school.id,
            BrandingData(),
            actor_id=admin_actor_id,
        )

        assert updated.motto == "New Motto"
        assert updated.address == "New Address"

        # Not supplied, therefore unchanged.
        assert updated.phone == "08000000000"


def test_update_branding_persists_changes(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        class BrandingData:
            def model_dump(self, exclude_unset=False):
                return {
                    "logo_url": "https://example.com/logo.png",
                    "primary_color": "#123456",
                }

        settings_service.update_branding(
            school.id,
            BrandingData(),
            actor_id=admin_actor_id,
        )

        persisted = _db.session.execute(
            _db.select(SchoolSettings).filter_by(
                school_id=school.id
            )
        ).scalar_one()

        assert persisted.logo_url == "https://example.com/logo.png"
        assert persisted.primary_color == "#123456"


def test_update_branding_does_not_clear_existing_value_with_none(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            motto="Existing Motto",
        )

        _db.session.add(settings)
        _db.session.commit()

        class BrandingData:
            def model_dump(self, exclude_unset=False):
                return {
                    "motto": None,
                }

        updated = settings_service.update_branding(
            school.id,
            BrandingData(),
            actor_id=admin_actor_id,
        )

        assert updated.motto == "Existing Motto"


# ======================================================================
# REPORT CARD SETTINGS
# ======================================================================


def test_update_report_card_settings_updates_supplied_fields(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        class ReportCardData:
            def model_dump(self, exclude_unset=False):
                return {
                    "show_logo_on_report": False,
                    "show_student_photo_on_report": False,
                    "show_ranking_on_report": True,
                }

        updated = settings_service.update_report_card_settings(
            school.id,
            ReportCardData(),
            actor_id=admin_actor_id,
        )

        assert updated.show_logo_on_report is False
        assert updated.show_student_photo_on_report is False
        assert updated.show_ranking_on_report is True


def test_update_report_card_settings_preserves_unsupplied_fields(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            show_logo_on_report=True,
            show_grade_on_report=False,
            show_attendance_on_report=True,
        )

        _db.session.add(settings)
        _db.session.commit()

        class ReportCardData:
            def model_dump(self, exclude_unset=False):
                return {
                    "show_logo_on_report": False,
                }

        updated = settings_service.update_report_card_settings(
            school.id,
            ReportCardData(),
            actor_id=admin_actor_id,
        )

        assert updated.show_logo_on_report is False
        assert updated.show_grade_on_report is False
        assert updated.show_attendance_on_report is True


# ======================================================================
# RESULT ACCESS SETTINGS
# ======================================================================


def test_update_result_access_settings_updates_values(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        class ResultAccessData:
            def model_dump(self, exclude_unset=False):
                return {
                    "require_result_pin": True,
                    "result_pin_length": 6,
                    "public_result_verification_enabled": False,
                }

        updated = settings_service.update_result_access_settings(
            school.id,
            ResultAccessData(),
            actor_id=admin_actor_id,
        )

        assert updated.require_result_pin is True
        assert updated.result_pin_length == 6
        assert updated.public_result_verification_enabled is False


def test_update_result_access_settings_preserves_unsupplied_values(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            require_result_pin=True,
            result_pin_length=6,
            public_result_verification_enabled=False,
        )

        _db.session.add(settings)
        _db.session.commit()

        class ResultAccessData:
            def model_dump(self, exclude_unset=False):
                return {
                    "result_pin_length": 8,
                }

        updated = settings_service.update_result_access_settings(
            school.id,
            ResultAccessData(),
            actor_id=admin_actor_id,
        )

        assert updated.require_result_pin is True
        assert updated.result_pin_length == 8
        assert updated.public_result_verification_enabled is False


# ======================================================================
# NOTIFICATION PREFERENCES
# ======================================================================


def test_update_notification_preferences_merges_preferences(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={
                "RESULT": {
                    "email": True,
                    "in_app": True,
                    "sms": False,
                },
                "ATTENDANCE": {
                    "email": True,
                },
            },
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.update_notification_preferences(
            school.id,
            {
                "RESULT": {
                    "email": False,
                    "sms": True,
                },
                "FEES": {
                    "email": True,
                    "sms": False,
                },
            },
            actor_id=admin_actor_id,
        )

        assert updated.notification_preferences == {
            "RESULT": {
                "email": False,
                "in_app": True,
                "sms": True,
            },
            "ATTENDANCE": {
                "email": True,
            },
            "FEES": {
                "email": True,
                "sms": False,
            },
        }


def test_update_notification_preferences_can_update_one_channel_without_replacing_type(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={
                "RESULT": {
                    "email": True,
                    "sms": False,
                    "push": True,
                },
            },
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.update_notification_preferences(
            school.id,
            {
                "RESULT": {
                    "email": False,
                },
            },
            actor_id=admin_actor_id,
        )

        # Deep merge:
        # email changes, while sms and push remain untouched.
        assert updated.notification_preferences["RESULT"] == {
            "email": False,
            "sms": False,
            "push": True,
        }


def test_update_notification_preferences_preserves_unmentioned_types(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={
                "RESULT": {
                    "email": True,
                },
                "ATTENDANCE": {
                    "sms": True,
                },
            },
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.update_notification_preferences(
            school.id,
            {
                "RESULT": {
                    "email": False,
                },
            },
            actor_id=admin_actor_id,
        )

        assert updated.notification_preferences == {
            "RESULT": {
                "email": False,
            },
            "ATTENDANCE": {
                "sms": True,
            },
        }


def test_update_notification_preferences_adds_new_notification_type(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={
                "RESULT": {
                    "email": True,
                },
            },
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.update_notification_preferences(
            school.id,
            {
                "FEES": {
                    "email": True,
                    "sms": False,
                },
            },
            actor_id=admin_actor_id,
        )

        assert updated.notification_preferences == {
            "RESULT": {
                "email": True,
            },
            "FEES": {
                "email": True,
                "sms": False,
            },
        }


def test_update_notification_preferences_empty_input_makes_no_change(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={
                "RESULT": {
                    "email": True,
                },
            },
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.update_notification_preferences(
            school.id,
            {},
            actor_id=admin_actor_id,
        )

        assert updated.notification_preferences == {
            "RESULT": {
                "email": True,
            },
        }


def test_update_notification_preferences_persists_to_database(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings_service.update_notification_preferences(
            school.id,
            {
                "RESULT": {
                    "email": True,
                    "in_app": True,
                },
            },
            actor_id=admin_actor_id,
        )

        _db.session.expire_all()

        persisted = _db.session.execute(
            _db.select(SchoolSettings).filter_by(
                school_id=school.id
            )
        ).scalar_one()

        assert persisted.notification_preferences == {
            "RESULT": {
                "email": True,
                "in_app": True,
            },
        }


def test_reset_notification_preferences(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={
                "RESULT": {
                    "email": True,
                    "sms": True,
                },
                "FEES": {
                    "email": False,
                },
            },
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.reset_notification_preferences(
            school.id,
            actor_id=admin_actor_id,
        )

        assert updated.notification_preferences == {}


def test_reset_notification_preferences_is_idempotent(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            notification_preferences={},
        )

        _db.session.add(settings)
        _db.session.commit()

        updated = settings_service.reset_notification_preferences(
            school.id,
            actor_id=admin_actor_id,
        )

        assert updated.notification_preferences == {}


# ======================================================================
# NO-OP UPDATES
# ======================================================================


def test_update_does_not_commit_or_audit_when_nothing_changes(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
            motto="Same Motto",
        )

        _db.session.add(settings)
        _db.session.commit()

        class BrandingData:
            def model_dump(self, exclude_unset=False):
                return {
                    "motto": "Same Motto",
                }

        updated = settings_service.update_branding(
            school.id,
            BrandingData(),
            actor_id=admin_actor_id,
        )

        assert updated.motto == "Same Motto"


# ======================================================================
# AUDIT LOGGING
# ======================================================================


def test_branding_update_creates_audit_log(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        class BrandingData:
            def model_dump(self, exclude_unset=False):
                return {
                    "motto": "Audited Motto",
                }

        updated = settings_service.update_branding(
            school.id,
            BrandingData(),
            actor_id=admin_actor_id,
        )

        logs = _get_audit_logs_for_settings(updated.id)

        assert len(logs) >= 1

        latest = logs[-1]

        assert latest.actor_id == admin_actor_id
        assert latest.resource_type == "SchoolSettings"
        assert latest.resource_id == updated.id


def test_notification_update_creates_audit_log(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        updated = settings_service.update_notification_preferences(
            school.id,
            {
                "RESULT": {
                    "email": True,
                },
            },
            actor_id=admin_actor_id,
        )

        logs = _get_audit_logs_for_settings(updated.id)

        assert len(logs) >= 1

        latest = logs[-1]

        assert latest.actor_id == admin_actor_id
        assert latest.resource_type == "SchoolSettings"
        assert latest.resource_id == updated.id


# ======================================================================
# SETTINGS CREATED ON UPDATE
# ======================================================================


def test_update_branding_creates_settings_if_missing(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        assert (
            _db.session.execute(
                _db.select(SchoolSettings).filter_by(
                    school_id=school.id
                )
            ).scalar_one_or_none()
            is None
        )

        class BrandingData:
            def model_dump(self, exclude_unset=False):
                return {
                    "motto": "Created Through Update",
                }

        updated = settings_service.update_branding(
            school.id,
            BrandingData(),
            actor_id=admin_actor_id,
        )

        assert updated.id is not None
        assert updated.school_id == school.id
        assert updated.motto == "Created Through Update"


def test_update_notification_preferences_creates_settings_if_missing(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        updated = settings_service.update_notification_preferences(
            school.id,
            {
                "RESULT": {
                    "email": True,
                },
            },
            actor_id=admin_actor_id,
        )

        assert updated.id is not None
        assert updated.school_id == school.id
        assert updated.notification_preferences == {
            "RESULT": {
                "email": True,
            },
        }


# ======================================================================
# SCHOOL ISOLATION
# ======================================================================


def test_each_school_has_independent_settings(
    app,
    school,
    admin_actor_id,
):
    with app.app_context():
        second_school = School(
            name="Second School",
            slug="second-school",
        )

        _db.session.add(second_school)
        _db.session.commit()

        first = settings_service.update_branding(
            school.id,
            type(
                "BrandingData",
                (),
                {
                    "model_dump": lambda self, exclude_unset=False: {
                        "motto": "First School Motto",
                    }
                },
            )(),
            actor_id=admin_actor_id,
        )

        second = settings_service.update_branding(
            second_school.id,
            type(
                "BrandingData",
                (),
                {
                    "model_dump": lambda self, exclude_unset=False: {
                        "motto": "Second School Motto",
                    }
                },
            )(),
            actor_id=admin_actor_id,
        )

        assert first.school_id != second.school_id
        assert first.motto == "First School Motto"
        assert second.motto == "Second School Motto"

        first_persisted = _db.session.execute(
            _db.select(SchoolSettings).filter_by(
                school_id=school.id
            )
        ).scalar_one()

        second_persisted = _db.session.execute(
            _db.select(SchoolSettings).filter_by(
                school_id=second_school.id
            )
        ).scalar_one()

        assert first_persisted.motto == "First School Motto"
        assert second_persisted.motto == "Second School Motto"


def test_school_cannot_have_duplicate_settings(
    app,
    school,
):
    with app.app_context():
        settings = SchoolSettings(
            school_id=school.id,
        )

        _db.session.add(settings)
        _db.session.commit()

        duplicate = SchoolSettings(
            school_id=school.id,
        )

        _db.session.add(duplicate)

        with pytest.raises(Exception):
            _db.session.commit()

        _db.session.rollback()


# ======================================================================
# DEFAULT VALUES
# ======================================================================


def test_new_settings_have_expected_default_values(
    app,
    school,
):
    with app.app_context():
        settings = settings_service.get_or_create_settings(
            school.id
        )

        assert settings.show_logo_on_report is True
        assert settings.show_student_photo_on_report is True
        assert settings.show_grade_on_report is True
        assert settings.show_attendance_on_report is True
        assert settings.show_teacher_remarks_on_report is True
        assert settings.show_principal_remarks_on_report is False
        assert settings.show_ranking_on_report is False
        assert settings.enable_class_ranking is False

        assert settings.require_result_pin is False
        assert settings.result_pin_length == 4
        assert settings.public_result_verification_enabled is True

        assert settings.notification_preferences == {}
