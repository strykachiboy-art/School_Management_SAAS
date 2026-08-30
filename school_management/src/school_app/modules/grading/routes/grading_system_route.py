from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.grading.requests.grading_system_request import (
    GradingSystemCreateRequest,
    GradingSystemUpdateRequest,
    GradingSystemResponse,
)
from school_app.modules.grading.requests.grading_rule_request import (
    GradingRuleCreateRequest,
    GradingRuleUpdateRequest,
    GradingRuleResponse,
)

from school_app.modules.grading.services.grading_system_service import (
    create_grading_system,
    get_all_grading_systems,
    get_grading_system,
    update_grading_system,
    delete_grading_system,
    create_grading_rule,
    update_grading_rule,
    delete_grading_rule,
)

grading_system_bp = Blueprint("grading_system", __name__, url_prefix="/grading-systems")


# ====================================== GradingSystem CRUD ===============================================

@grading_system_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(GradingSystemCreateRequest)
def create_system(data: GradingSystemCreateRequest):
    system = create_grading_system(data, actor_id=g.user.id)
    return jsonify(GradingSystemResponse.model_validate(system).model_dump()), 201


@grading_system_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_systems():
    include_inactive = request.args.get("include_inactive", False, type=bool)
    systems = get_all_grading_systems(include_inactive=include_inactive)
    return jsonify([GradingSystemResponse.model_validate(s).model_dump() for s in systems]), 200


@grading_system_bp.route("/<int:system_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_system(system_id):
    system = get_grading_system(system_id)
    if system is None:
        abort(404, description="Grading system not found")
    return jsonify(GradingSystemResponse.model_validate(system).model_dump()), 200


@grading_system_bp.route("/<int:system_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(GradingSystemUpdateRequest)
def update_system(data: GradingSystemUpdateRequest, system_id):
    system = update_grading_system(data, system_id, actor_id=g.user.id)
    if system is None:
        abort(404, description="Grading system not found")
    return jsonify(GradingSystemResponse.model_validate(system).model_dump()), 200


@grading_system_bp.route("/<int:system_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_system(system_id):
    if not delete_grading_system(system_id, actor_id=g.user.id):
        abort(404, description="Grading system not found")
    return jsonify({"message": "Grading system deleted successfully"}), 200


# ====================================== GradingRule CRUD ===============================================
# Nested under grading_system_bp's blueprint but its own URL prefix, since a
# rule always belongs to a system but is addressed by its own id for
# update/delete — same pattern as academic_level under academic_stage.

grading_rule_bp = Blueprint("grading_rule", __name__, url_prefix="/grading-rules")


@grading_rule_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(GradingRuleCreateRequest)
def create_rule(data: GradingRuleCreateRequest):
    rule = create_grading_rule(data, actor_id=g.user.id)
    return jsonify(GradingRuleResponse.model_validate(rule).model_dump()), 201


@grading_rule_bp.route("/<int:rule_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(GradingRuleUpdateRequest)
def update_rule(data: GradingRuleUpdateRequest, rule_id):
    rule = update_grading_rule(data, rule_id, actor_id=g.user.id)
    if rule is None:
        abort(404, description="Grading rule not found")
    return jsonify(GradingRuleResponse.model_validate(rule).model_dump()), 200


@grading_rule_bp.route("/<int:rule_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_rule(rule_id):
    if not delete_grading_rule(rule_id, actor_id=g.user.id):
        abort(404, description="Grading rule not found")
    return jsonify({"message": "Grading rule deleted successfully"}), 200