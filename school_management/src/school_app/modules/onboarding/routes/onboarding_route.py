from flask import Blueprint, jsonify, g
from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request

from school_app.modules.onboarding.requests.onboarding_request import (
    SchoolInfoStepRequest, LocalizationStepRequest, AcademicStructureStepRequest,
    GradingConfigStepRequest, PromotionConfigStepRequest, AdminAccountStepRequest,
    OnboardingProgressResponse,
)
from school_app.modules.onboarding.services.onboarding_service import (
    get_or_create_progress, submit_school_info, submit_localization,
    submit_academic_structure, submit_grading_config, submit_promotion_config,
    submit_admin_account, complete_onboarding,
)

onboarding_bp = Blueprint("onboarding", __name__, url_prefix="/onboarding")


def _resp(progress):
    return jsonify(OnboardingProgressResponse.model_validate(progress).model_dump()), 200


@onboarding_bp.route("/<int:school_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
def get_onboarding_progress_route(school_id):
    return _resp(get_or_create_progress(school_id))


@onboarding_bp.route("/<int:school_id>/school-info", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(SchoolInfoStepRequest)
def submit_school_info_route(data, school_id):
    return _resp(submit_school_info(school_id, data, actor_id=g.user.id))


@onboarding_bp.route("/<int:school_id>/localization", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(LocalizationStepRequest)
def submit_localization_route(data, school_id):
    return _resp(submit_localization(school_id, data, actor_id=g.user.id))


@onboarding_bp.route("/<int:school_id>/academic-structure", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(AcademicStructureStepRequest)
def submit_academic_structure_route(data, school_id):
    return _resp(submit_academic_structure(school_id, data, actor_id=g.user.id))


@onboarding_bp.route("/<int:school_id>/grading-config", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(GradingConfigStepRequest)
def submit_grading_config_route(data, school_id):
    return _resp(submit_grading_config(school_id, data, actor_id=g.user.id))


@onboarding_bp.route("/<int:school_id>/promotion-config", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(PromotionConfigStepRequest)
def submit_promotion_config_route(data, school_id):
    return _resp(submit_promotion_config(school_id, data, actor_id=g.user.id))


@onboarding_bp.route("/<int:school_id>/admin-account", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
@validate_request(AdminAccountStepRequest)
def submit_admin_account_route(data, school_id):
    return _resp(submit_admin_account(school_id, data, actor_id=g.user.id))


@onboarding_bp.route("/<int:school_id>/complete", methods=["POST"])
@role_required(Role.ADMIN, Role.PLATFORM_ADMIN)
def complete_onboarding_route(school_id):
    return _resp(complete_onboarding(school_id, actor_id=g.user.id))