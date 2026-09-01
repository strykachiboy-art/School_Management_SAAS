from flask import Blueprint, jsonify, request, abort, g

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request
from school_app.modules.grading.requests.result_request import (
    ResultCreateRequest,
    ResultResponse,
)
from school_app.modules.grading.services.result_service import (
    create_result,
    get_result as get_result_by_id,
    get_all_result as get_all_result_service,
    delete_result,
    search_results,
    paginate_result,
)

result_bp = Blueprint("result", __name__, url_prefix="/results")


# ======================================================================
# Create Result Route
# ======================================================================

@result_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
@validate_request(ResultCreateRequest)
def create_result_route(data: ResultCreateRequest):
    created_result = create_result(
        student_id=data.student_id,
        exam_id=data.exam_id,
        marks_obtained=data.marks_obtained,
        actor_id=g.user.id,
    )
    serialized_result = ResultResponse.model_validate(
        created_result
    ).model_dump()

    return jsonify(serialized_result), 201


# ======================================================================
# Get All Results Route
# ======================================================================

@result_bp.route("/", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_all_results_route():
    results = get_all_result_service()
    serialized_results = [
        ResultResponse.model_validate(result).model_dump()
        for result in results
    ]

    return jsonify(serialized_results), 200


# ======================================================================
# Get Result by ID Route
# ======================================================================

@result_bp.route("/<int:result_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_result_route(result_id):
    result = get_result_by_id(result_id)
    if not result:
        abort(404, description="Result not found")

    serialized_result = ResultResponse.model_validate(result).model_dump()

    return jsonify(serialized_result), 200


# ======================================================================
# Delete Result Route
# ======================================================================

@result_bp.route("/<int:result_id>/delete", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_result_route(result_id):
    deleted = delete_result(
        result_id,
        actor_id=g.user.id,
    )
    if not deleted:
        abort(404, description="Result not found")

    return jsonify({"message": "Result deleted successfully"}), 200


# ======================================================================
# Search Result Route
# ======================================================================

@result_bp.route("/search", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def search_result_route():
    try:
        student_id = request.args.get("student_id", type=int)
        exam_id = request.args.get("exam_id", type=int)

        if request.args.get("paginate") == "true":
            page = paginate_result()

            return jsonify(
                {
                    "items": [
                        ResultResponse.model_validate(result).model_dump()
                        for result in page.items
                    ],
                    "page": page.page,
                    "pages": page.pages,
                    "total": page.total,
                }
            ), 200

        if student_id is not None or exam_id is not None:
            results = search_results(
                student_id=student_id,
                exam_id=exam_id,
            )
        else:
            results = get_all_result_service()

        serialized_results = [
            ResultResponse.model_validate(result).model_dump()
            for result in results
        ]

        return jsonify(serialized_results), 200

    except Exception:
        abort(500, description="An unexpected error occurred.")