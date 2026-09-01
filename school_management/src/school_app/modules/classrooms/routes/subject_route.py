from flask import Blueprint, jsonify, request, abort, g

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.utils.helpers import validate_request

from school_app.modules.classrooms.requests.subject_request import (
    SubjectCreateRequest,
    SubjectResponse,
)

from school_app.modules.classrooms.services.subject_service import (
    create_subject,
    get_subject,
    get_all_subjects,
    update_subject,
    delete_subject,
    search_subject_info,
    paginate_subject,
)


subject_bp = Blueprint(
    "subject",
    __name__,
    url_prefix="/subjects",
)


# ====================================== Create Subject ======================================

@subject_bp.route("/create", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(SubjectCreateRequest)
def create_subject_route(data: SubjectCreateRequest):
    subject = create_subject(
        data,
        actor_id=g.user.id,
    )

    serialized_subject = SubjectResponse.model_validate(
        subject
    ).model_dump()

    return jsonify(serialized_subject), 201


# ====================================== Get Subjects ======================================

@subject_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_subjects():
    school_id = g.user.school_id
    search = request.args.get("search", "", type=str)

    if request.args.get("paginate") == "true":
        page = paginate_subject(
            school_id=school_id,
        )

        return jsonify({
            "items": [
                SubjectResponse.model_validate(item).model_dump()
                for item in page.items
            ],
            "page": page.page,
            "pages": page.pages,
            "total": page.total,
        }), 200

    if search:
        subjects = search_subject_info(
            search,
            school_id=school_id,
        )
    else:
        subjects = get_all_subjects(
            school_id=school_id,
        )

    serialized_subjects = [
        SubjectResponse.model_validate(subject).model_dump()
        for subject in subjects
    ]

    return jsonify(serialized_subjects), 200


# ====================================== Get Subject Detail ======================================

@subject_bp.route("/<int:subject_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_subject_detail(subject_id):
    subject = get_subject(subject_id)

    if subject is None:
        abort(404, description="Subject not found")

    if subject.school_id != g.user.school_id:
        abort(404, description="Subject not found")

    serialized_subject = SubjectResponse.model_validate(
        subject
    ).model_dump()

    return jsonify(serialized_subject), 200


# ====================================== Update Subject ======================================

@subject_bp.route("/<int:subject_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(SubjectCreateRequest)
def update_subject_route(
    data: SubjectCreateRequest,
    subject_id,
):
    subject = update_subject(
        subject_id,
        data,
        actor_id=g.user.id,
    )

    if subject is None:
        abort(404, description="Subject not found")

    serialized_subject = SubjectResponse.model_validate(
        subject
    ).model_dump()

    return jsonify(serialized_subject), 200


# ====================================== Delete Subject ======================================

@subject_bp.route("/<int:subject_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_subject_route(subject_id):
    deleted = delete_subject(
        subject_id,
        actor_id=g.user.id,
    )

    if not deleted:
        abort(404, description="Subject not found")

    return jsonify({
        "message": "Subject deleted successfully"
    }), 200
