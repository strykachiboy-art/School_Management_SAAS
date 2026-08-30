from flask import Blueprint, jsonify, request, abort, g
from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role
from school_app.extensions import limiter

from school_app.modules.grading.requests.report_card_request import (
    ReportCardCalculateRequest,
    ReportCardStatusUpdateRequest,
    ReportCardSetPinRequest,
    ReportCardPublicVerifyRequest,
    ReportCardResponse,
)

from school_app.modules.grading.services.report_card_service import ReportCardService

report_card_bp = Blueprint("report_card", __name__, url_prefix="/report-cards")


# ====================================== calculate_report ===============================================

@report_card_bp.route("/calculate", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
@validate_request(ReportCardCalculateRequest)
def calculate_report(data: ReportCardCalculateRequest):
    report = ReportCardService.generate_or_calculate(
        student_id=data.student_id,
        session_id=data.academic_session_id,
        term_id=data.term_id,
    )
    serialized = ReportCardResponse.model_validate(report).model_dump()
    return jsonify(serialized), 200


# ====================================== transition_status ===============================================

@report_card_bp.route("/<int:report_id>/status", methods=["PATCH"])
@role_required(Role.ADMIN, Role.TEACHER, Role.HEAD_TEACHER, Role.PRINCIPAL)
@validate_request(ReportCardStatusUpdateRequest)
def transition_status(data: ReportCardStatusUpdateRequest, report_id: int):
    # Retrieve user role from global g context set by authentication middleware
    user_role = g.user.role.value if hasattr(g.user, "role") else "guest"
    
    report = ReportCardService.transition_status(
        report_id=report_id,
        target_status=data.status,
        user_role=user_role,
    )
    serialized = ReportCardResponse.model_validate(report).model_dump()
    return jsonify(serialized), 200


# ====================================== set_access_pin ===============================================

@report_card_bp.route("/<int:report_id>/pin", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(ReportCardSetPinRequest)
def set_pin(data: ReportCardSetPinRequest, report_id: int):
    report = ReportCardService.set_access_pin(
        report_id=report_id,
        raw_pin=data.pin,
    )
    return jsonify({"message": "Access PIN updated successfully"}), 200


# ====================================== public_verify ===============================================

@report_card_bp.route("/public/verify", methods=["POST"])
@limiter.limit("5 per minute")
@validate_request(ReportCardPublicVerifyRequest)
def public_verify(data: ReportCardPublicVerifyRequest):
    report = ReportCardService.verify_and_fetch_public(
        public_ref=data.reference,
        raw_pin=data.pin,
    )
    serialized = ReportCardResponse.model_validate(report).model_dump()
    return jsonify(serialized), 200