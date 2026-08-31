from flask import Blueprint, jsonify, request, abort, g
from sqlalchemy.exc import IntegrityError
from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request
from school_app.modules.grading.requests.exam_request import ExamCreateRequest, ExamUpdateRequest, ExamResponse
from school_app.modules.grading.services.exam_service import (
    create_exam,
    get_exam as get_exam_by_id,
    get_all_exam,
    update_exam,
    delete_exam,
    search_exams,
    paginate_exams
)

exam_bp = Blueprint('exam', __name__, url_prefix="/exams")


@exam_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(ExamCreateRequest)
def create_exam_route(data: ExamCreateRequest):
    try:
        created_exam = create_exam(data, school_id=g.user.school_id, actor_id=g.user.id)

        if created_exam is None:
            return jsonify({"error": "Could not create exam"}), 400

        serialized_exam = ExamResponse.model_validate(created_exam).model_dump(mode="json")
        return jsonify(serialized_exam), 201

    except IntegrityError:
        return jsonify({"error": "Database error — duplicate or invalid constraint."}), 400


@exam_bp.route("/", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_exams():
    try:
        search = request.args.get("search", "", type=str)
        subject_id = request.args.get("subject_id", None, type=int)
        classroom_id = request.args.get("classroom_id", None, type=int)

        if request.args.get("paginate") == "true":
            page = paginate_exams(school_id=g.user.school_id)
            return jsonify({
                "items": [ExamResponse.model_validate(item).model_dump(mode="json") for item in page.items],
                "page": page.page,
                "pages": page.pages,
                "total": page.total,
            }), 200
        elif search or subject_id or classroom_id:
            exams = search_exams(school_id=g.user.school_id, search=search, subject_id=subject_id, classroom_id=classroom_id)
        else:
            exams = get_all_exam(school_id=g.user.school_id)

        serialized_exams = [ExamResponse.model_validate(e).model_dump(mode="json") for e in exams]
        return jsonify(serialized_exams), 200

    except Exception as e:
        abort(500, description="An unexpected error occurred.")


@exam_bp.route("/<int:exam_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_exam(exam_id):
    exam = get_exam_by_id(exam_id, school_id=g.user.school_id)
    if exam is None:
        abort(404, description="Exam not found")

    serialized_exam = ExamResponse.model_validate(exam).model_dump(mode="json")
    return jsonify(serialized_exam), 200


@exam_bp.route("/<int:exam_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(ExamUpdateRequest)
def update_exam_route(data: ExamUpdateRequest, exam_id):
    exam = get_exam_by_id(exam_id, school_id=g.user.school_id)
    if exam is None:
        abort(404, description="Exam not found")

    updated_exam = update_exam(exam_id, data, school_id=g.user.school_id, actor_id=g.user.id)

    serialized_exam = ExamResponse.model_validate(updated_exam).model_dump(mode="json")
    return jsonify(serialized_exam), 200


@exam_bp.route("/<int:exam_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def remove_exam(exam_id):
    deleted = delete_exam(exam_id, school_id=g.user.school_id, actor_id=g.user.id)

    if not deleted:
        abort(404, description="Exam not found")

    return jsonify({"message": "Exam deleted successfully"}), 200