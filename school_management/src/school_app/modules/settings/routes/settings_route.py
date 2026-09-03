from flask import Blueprint, jsonify, g
from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request

from school_app.modules.settings.requests.settings_request import (
    BrandingSettingsRequest, ReportCardSettingsRequest,
    ResultAccessSettingsRequest, NotificationPreferencesRequest,
    SchoolSettingsResponse,
)
from school_app.modules.settings.services import settings_service

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")


def _resp(settings):
    return jsonify(SchoolSettingsResponse.model_validate(settings).model_dump()), 200


@settings_bp.route("/<int:school_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
def get_settings_route(school_id):
    return _resp(settings_service.get_or_create_settings(school_id))


@settings_bp.route("/<int:school_id>/branding", methods=["PATCH"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(BrandingSettingsRequest)
def update_branding_route(data, school_id):
    return _resp(settings_service.update_branding(school_id, data, actor_id=g.user.id))


@settings_bp.route("/<int:school_id>/report-card", methods=["PATCH"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(ReportCardSettingsRequest)
def update_report_card_route(data, school_id):
    return _resp(settings_service.update_report_card_settings(school_id, data, actor_id=g.user.id))


@settings_bp.route("/<int:school_id>/result-access", methods=["PATCH"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(ResultAccessSettingsRequest)
def update_result_access_route(data, school_id):
    return _resp(settings_service.update_result_access_settings(school_id, data, actor_id=g.user.id))


@settings_bp.route("/<int:school_id>/notifications", methods=["PATCH"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(NotificationPreferencesRequest)
def update_notification_preferences_route(data, school_id):
    return _resp(settings_service.update_notification_preferences(
        school_id, data.preferences, actor_id=g.user.id
    ))
    
    
@settings_bp.route("/<int:school_id>/notifications/reset", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
def reset_notification_preferences_route(school_id):
    return _resp(settings_service.reset_notification_preferences(school_id, actor_id=g.user.id))