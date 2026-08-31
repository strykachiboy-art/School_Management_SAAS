from flask import Blueprint, jsonify, g, abort, request

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request
from school_app.enums.promotion import PromotionDecision
from school_app.modules.promotion.requests.promotion_request import (
    PromotionEvaluationResponse,
    PromoteStudentRequest,
    RepeatStudentRequest,
    GraduateStudentRequest,
    PromotionHistoryResponse,
    BulkPromoteRequest,
    BulkPromoteResponse,
)
from school_app.modules.promotion.services.promotion_service import (
    evaluate_student_promotion,
    promote_student as promote_student_service,
    repeat_student as repeat_student_service,
    graduate_student as graduate_student_service,
    get_student_promotion_history,
    get_session_promotions,
    promote_session_students,
)

promotion_bp = Blueprint("promotion", __name__, url_prefix="/promotions")

# ====================================== evaluate_promotion_route ===============================================

@promotion_bp.route("/students/<int:student_id>/sessions/<int:academic_session_id>/evaluate", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def evaluate_promotion_route(student_id, academic_session_id):
    school_id = getattr(g.user, "school_id", None) if g.user else None
    evaluation = evaluate_student_promotion(
        student_id, 
        academic_session_id, 
        school_id=school_id
    )

    if evaluation is None:
        abort(404, description="Student or academic session not found")

    serialized = PromotionEvaluationResponse.model_validate(evaluation).model_dump()
    return jsonify(serialized), 200


# ====================================== promote_student_route ===============================================

@promotion_bp.route("/students/<int:student_id>/sessions/<int:academic_session_id>/promote", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
@validate_request(PromoteStudentRequest)
def promote_student_route(data: PromoteStudentRequest, student_id, academic_session_id):
    school_id = getattr(g.user, "school_id", None) if g.user else None
    user_id = g.user.id if g.user else None
    user_role = g.user.role if g.user else None

    try:
        history = promote_student_service(
            student_id,
            academic_session_id,
            data.to_classroom_id,
            school_id=school_id,
            remarks=data.remarks,
            decided_by=user_id,
            decided_by_role=user_role,
            allow_level_skip=data.allow_level_skip,
            actor_id=user_id
        )
    except ValueError as err:
        abort(400, description=str(err))
    except PermissionError as err:
        abort(403, description=str(err))

    if history is None:
        abort(404, description="Student not found")

    serialized = PromotionHistoryResponse.model_validate(history).model_dump()
    return jsonify(serialized), 201


# ====================================== repeat_student_route ===============================================

@promotion_bp.route("/students/<int:student_id>/sessions/<int:academic_session_id>/repeat", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(RepeatStudentRequest)
def repeat_student_route(data: RepeatStudentRequest, student_id, academic_session_id):
    school_id = getattr(g.user, "school_id", None) if g.user else None
    user_id = g.user.id if g.user else None

    history = repeat_student_service(
        student_id,
        academic_session_id,
        school_id=school_id,
        remarks=data.remarks,
        decided_by=user_id,
        actor_id=user_id
    )

    if history is None:
        abort(404, description="Student not found")

    serialized = PromotionHistoryResponse.model_validate(history).model_dump()
    return jsonify(serialized), 201


# ====================================== graduate_student_route ===============================================

@promotion_bp.route("/students/<int:student_id>/sessions/<int:academic_session_id>/graduate", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(GraduateStudentRequest)
def graduate_student_route(data: GraduateStudentRequest, student_id, academic_session_id):
    school_id = getattr(g.user, "school_id", None) if g.user else None
    user_id = g.user.id if g.user else None

    history = graduate_student_service(
        student_id,
        academic_session_id,
        school_id=school_id,
        remarks=data.remarks,
        decided_by=user_id,
        actor_id=user_id
    )

    if history is None:
        abort(404, description="Student not found")

    serialized = PromotionHistoryResponse.model_validate(history).model_dump()
    return jsonify(serialized), 201


# ====================================== student_promotion_history_route ===============================================

@promotion_bp.route("/students/<int:student_id>/history", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def student_promotion_history_route(student_id):
    user_role = getattr(g.user, "role", None)
    
    # Check if student role matches either string or Enum value safely
    if user_role in (Role.STUDENT, Role.STUDENT.value, "student"):
        student_profile_id = getattr(getattr(g.user, "student_profile", None), "id", None)
        if student_profile_id != student_id:
            abort(403, description="Students may only view their own promotion history")

    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        abort(400, description="page and per_page must be integers")

    school_id = getattr(g.user, "school_id", None) if g.user else None

    result = get_student_promotion_history(
        student_id, 
        school_id=school_id, 
        page=page, 
        per_page=per_page
    )

    if result is None:
        abort(404, description="Student not found")

    serialized = {
        "items": [PromotionHistoryResponse.model_validate(h).model_dump() for h in result["items"]],
        "page": result["page"],
        "per_page": result["per_page"],
        "total": result["total"],
        "total_pages": result["total_pages"],
    }
    return jsonify(serialized), 200


# ====================================== session_promotions_route ===============================================

@promotion_bp.route("/sessions/<int:academic_session_id>", methods=["GET"])
@role_required(Role.ADMIN)
def session_promotions_route(academic_session_id):
    decision_param = request.args.get("decision")
    classroom_id_param = request.args.get("classroom_id")

    decision = None
    if decision_param:
        try:
            # Handle string case dynamically (e.g. uppercase vs lowercase)
            formatted_param = decision_param.strip().upper()
            decision = PromotionDecision[formatted_param]
        except (KeyError, ValueError):
            try:
                decision = PromotionDecision(decision_param.lower())
            except ValueError:
                abort(
                    400,
                    description=f"Invalid decision '{decision_param}'. Must be one of: "
                    f"{', '.join(d.value for d in PromotionDecision)}",
                )

    classroom_id = None
    if classroom_id_param:
        try:
            classroom_id = int(classroom_id_param)
        except ValueError:
            abort(400, description="classroom_id must be an integer")

    school_id = getattr(g.user, "school_id", None) if g.user else None

    promotions = get_session_promotions(
        academic_session_id, 
        school_id=school_id, 
        decision=decision, 
        classroom_id=classroom_id
    )

    if promotions is None:
        abort(404, description="Academic session not found")

    serialized = [PromotionHistoryResponse.model_validate(p).model_dump() for p in promotions]
    return jsonify(serialized), 200


# ====================================== bulk_promote_session_route ===============================================

@promotion_bp.route("/sessions/<int:academic_session_id>/bulk-promote", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(BulkPromoteRequest)
def bulk_promote_session_route(data: BulkPromoteRequest, academic_session_id):
    school_id = getattr(g.user, "school_id", None) if g.user else None
    user_id = g.user.id if g.user else None

    try:
        results = promote_session_students(
            academic_session_id,
            school_id=school_id,
            classroom_id=data.classroom_id,
            decided_by=user_id,
            actor_id=user_id
        )
    except ValueError as err:
        abort(404, description=str(err))

    serialized = BulkPromoteResponse.model_validate(results).model_dump()
    return jsonify(serialized), 200