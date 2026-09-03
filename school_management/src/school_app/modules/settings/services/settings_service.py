from flask import abort
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.enums.audit import AuditAction
from school_app.models.school import School
from school_app.models.school_settings import SchoolSettings
from school_app.modules.audit.services.audit_log_service import create_audit_log


# ======================================================================
# SCHOOL SETTINGS SERVICE
# ======================================================================


def get_or_create_settings(school_id: int) -> SchoolSettings:
    """
    Return the school's settings.

    If the school exists but does not have settings yet, create the
    default SchoolSettings record.
    """
    settings = db.session.execute(
        db.select(SchoolSettings).filter_by(school_id=school_id)
    ).scalar_one_or_none()

    if settings is not None:
        return settings

    school = db.session.get(School, school_id)

    if school is None:
        abort(404, description="School not found")

    settings = SchoolSettings(school_id=school_id)

    db.session.add(settings)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create school settings.")

    return settings


def _apply_update(
    settings: SchoolSettings,
    data,
    actor_id: int,
    description: str,
) -> SchoolSettings:
    """
    Shared update-and-audit path.

    Only fields explicitly supplied in the request are considered.
    None values are ignored so PATCH requests cannot accidentally clear
    existing values.

    An audit log is created only when an actual value changes.
    """
    changes = {}

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            continue

        current = getattr(settings, field)

        if current == value:
            continue

        changes[field] = {
            "before": current,
            "after": value,
        }

        setattr(settings, field, value)

    # Nothing changed.
    if not changes:
        return settings

    try:
        db.session.flush()

        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="SchoolSettings",
            resource_id=settings.id,
            description=description,
            changes=changes,
            school_id=settings.school_id,
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not save settings.")

    return settings


def update_branding(
    school_id: int,
    data,
    actor_id: int,
) -> SchoolSettings:
    """
    Update school profile and branding settings.
    """
    settings = get_or_create_settings(school_id)

    return _apply_update(
        settings,
        data,
        actor_id,
        "Updated school branding settings",
    )


def update_report_card_settings(
    school_id: int,
    data,
    actor_id: int,
) -> SchoolSettings:
    """
    Update report-card display settings.
    """
    settings = get_or_create_settings(school_id)

    return _apply_update(
        settings,
        data,
        actor_id,
        "Updated report card display settings",
    )


def update_result_access_settings(
    school_id: int,
    data,
    actor_id: int,
) -> SchoolSettings:
    """
    Update result-access and result-PIN settings.
    """
    settings = get_or_create_settings(school_id)

    return _apply_update(
        settings,
        data,
        actor_id,
        "Updated result access settings",
    )


def update_notification_preferences(
    school_id: int,
    preferences: dict,
    actor_id: int,
) -> SchoolSettings:
    """
    Update school-level notification preferences.

    Notification preferences are deep-merged.

    Example:

        Existing:
        {
            "RESULT": {
                "email": True,
                "sms": True,
                "push": False
            }
        }

        Incoming:
        {
            "RESULT": {
                "email": False
            }
        }

        Result:
        {
            "RESULT": {
                "email": False,
                "sms": True,
                "push": False
            }
        }

    Existing notification types that are not mentioned are preserved.
    Existing channels that are not mentioned are also preserved.
    """
    settings = get_or_create_settings(school_id)

    old = dict(settings.notification_preferences or {})

    # Start with a copy so we never mutate the existing JSON structure
    # in place.
    merged = {
        notification_type: dict(channels)
        for notification_type, channels in old.items()
    }

    for notification_type, channels in preferences.items():
        existing_channels = merged.setdefault(
            notification_type,
            {},
        )

        existing_channels.update(channels)

    # No actual changes.
    if merged == old:
        return settings

    settings.notification_preferences = merged

    changes = {
        "notification_preferences": {
            "before": old,
            "after": merged,
        }
    }

    try:
        db.session.flush()

        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="SchoolSettings",
            resource_id=settings.id,
            description="Updated notification preferences",
            changes=changes,
            school_id=settings.school_id,
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="Could not save notification preferences.",
        )

    return settings


def reset_notification_preferences(
    school_id: int,
    actor_id: int,
) -> SchoolSettings:
    """
    Reset notification preferences to the school's default empty state.
    """
    settings = get_or_create_settings(school_id)

    old = dict(settings.notification_preferences or {})

    # Already reset — no database write or audit entry is necessary.
    if not old:
        return settings

    settings.notification_preferences = {}

    changes = {
        "notification_preferences": {
            "before": old,
            "after": {},
        }
    }

    try:
        db.session.flush()

        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="SchoolSettings",
            resource_id=settings.id,
            description="Reset notification preferences to default",
            changes=changes,
            school_id=school_id,
        )

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="Could not reset notification preferences.",
        )

    return settings

