from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role

from school_app.modules.promotion.requests.promotion_rule_request import (
    PromotionRuleCreateRequest,
    PromotionRuleUpdateRequest,
    PromotionRuleResponse,
)

from school_app.modules.promotion.services.promotion_rule_service import (
    create_promotion_rule,
    get_all_promotion_rules,
    get_promotion_rule,
    update_promotion_rule,
    delete_promotion_rule,
)

promotion_rule_bp = Blueprint("promotion_rule", __name__, url_prefix="/promotion-rules")


# ====================================== create_promotion_rule ===============================================

@promotion_rule_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(PromotionRuleCreateRequest)
def create_rule(data: PromotionRuleCreateRequest):
    rule = create_promotion_rule(data, actor_id=g.user.id)
    return jsonify(PromotionRuleResponse.model_validate(rule).model_dump()), 201


# ====================================== get_all_promotion_rules ===============================================

@promotion_rule_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_rules():
    from_level_id = request.args.get("from_level_id", None, type=int)
    include_inactive = request.args.get("include_inactive", False, type=bool)
    rules = get_all_promotion_rules(from_level_id=from_level_id, include_inactive=include_inactive)
    return jsonify([PromotionRuleResponse.model_validate(r).model_dump() for r in rules]), 200


# ====================================== get_promotion_rule ===============================================

@promotion_rule_bp.route("/<int:rule_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_rule(rule_id):
    rule = get_promotion_rule(rule_id)
    if rule is None:
        abort(404, description="Promotion rule not found")
    return jsonify(PromotionRuleResponse.model_validate(rule).model_dump()), 200


# ====================================== update_promotion_rule ===============================================

@promotion_rule_bp.route("/<int:rule_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(PromotionRuleUpdateRequest)
def update_rule(data: PromotionRuleUpdateRequest, rule_id):
    rule = update_promotion_rule(data, rule_id, actor_id=g.user.id)
    if rule is None:
        abort(404, description="Promotion rule not found")
    return jsonify(PromotionRuleResponse.model_validate(rule).model_dump()), 200


# ====================================== delete_promotion_rule ===============================================

@promotion_rule_bp.route("/<int:rule_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_rule(rule_id):
    if not delete_promotion_rule(rule_id, actor_id=g.user.id):
        abort(404, description="Promotion rule not found")
    return jsonify({"message": "Promotion rule deleted successfully"}), 200