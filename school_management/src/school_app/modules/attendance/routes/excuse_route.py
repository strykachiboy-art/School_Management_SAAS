from flask import Blueprint, jsonify, request, g, abort
from pydantic import ValidationError

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.enums.excuse import ExcuseStatus

from school_app.modules.attendance.requests.excuse_request import (
    ExcuseCreateRequest,
    ExcuseUpdateRequest,
    ExcuseResponse,
    BulkExcuseReviewRequest,
)

from school_app.modules.attendance.services import excuse_service

excuse_bp = Blueprint(
    "excuse_bp",
    __name__,
    url_prefix="/excuses",
)


def _current_student_id() -> int:
    """Return the authenticated student's profile ID."""
    student = getattr(g.user, "student_profile", None)

    if student is None:
        abort(
            403,
            description="Student profile not found.",
        )

    return student.id


def _serialize_excuse(excuse):
    return ExcuseResponse.model_validate(
        excuse
    ).model_dump(mode="json")


def _serialize_excuses(excuses):
    return [
        _serialize_excuse(excuse)
        for excuse in excuses
    ]


def _assert_student_owns_excuse(excuse):
    """Prevent a student from viewing another student's excuse."""
    student_id = _current_student_id()

    if not excuse.attendance:
        abort(
            404,
            description="Attendance record associated with excuse not found.",
        )

    if excuse.attendance.student_id != student_id:
        abort(
            403,
            description="You can only view your own excuses.",
        )


# ======================================================================
# POST /excuses
# ======================================================================

@excuse_bp.route("", methods=["POST"])
@role_required(Role.STUDENT)
def create_excuse():
    try:
        data = ExcuseCreateRequest.model_validate(
            request.get_json() or {}
        )
    except ValidationError as err:
        return jsonify({
            "errors": err.errors()
        }), 400

    excuse = excuse_service.create_excuse(
        attendance_id=data.attendance_id,
        reason=data.reason,
        student_id=_current_student_id(),
        actor_id=g.user.id,
    )

    return jsonify(
        _serialize_excuse(excuse)
    ), 201


# ======================================================================
# GET /excuses/<id>
# ======================================================================

@excuse_bp.route("/<int:excuse_id>", methods=["GET"])
@role_required(
    Role.ADMIN,
    Role.TEACHER,
    Role.STUDENT,
)
def get_excuse(excuse_id: int):
    excuse = excuse_service.get_excuse(excuse_id)

    if g.user.role == Role.STUDENT:
        _assert_student_owns_excuse(excuse)

    return jsonify(
        _serialize_excuse(excuse)
    ), 200


# ======================================================================
# GET /excuses
# ======================================================================

@excuse_bp.route("", methods=["GET"])
@role_required(
    Role.ADMIN,
    Role.TEACHER,
    Role.STUDENT,
)
def get_excuses():
    student_id = request.args.get(
        "student_id",
        type=int,
    )

    term_id = request.args.get(
        "term_id",
        type=int,
    )

    raw_status = request.args.get(
        "status",
        type=str,
    )

    status = None

    if raw_status:
        try:
            status = ExcuseStatus(
                raw_status.lower()
            )
        except ValueError:
            return jsonify({
                "error": (
                    f"Invalid status parameter "
                    f"'{raw_status}'"
                )
            }), 400

    # Students can only request their own excuses.
    if g.user.role == Role.STUDENT:
        current_student_id = _current_student_id()

        if (
            student_id is not None
            and student_id != current_student_id
        ):
            abort(
                403,
                description="You can only view your own excuses.",
            )

        student_id = current_student_id

    school_id = getattr(
        g.user,
        "school_id",
        None,
    )

    excuses = excuse_service.get_excuses(
        student_id=student_id,
        term_id=term_id,
        status=status,
        school_id=school_id,
    )

    return jsonify(
        _serialize_excuses(excuses)
    ), 200


# ======================================================================
# PATCH /excuses/<id>
# ======================================================================

@excuse_bp.route("/<int:excuse_id>", methods=["PATCH"])
@role_required(Role.STUDENT)
def update_excuse(excuse_id: int):
    try:
        data = ExcuseUpdateRequest.model_validate(
            request.get_json() or {}
        )
    except ValidationError as err:
        return jsonify({
            "errors": err.errors()
        }), 400

    excuse = excuse_service.update_excuse(
        excuse_id=excuse_id,
        reason=data.reason,
        student_id=_current_student_id(),
        actor_id=g.user.id,
    )

    return jsonify(
        _serialize_excuse(excuse)
    ), 200


# ======================================================================
# DELETE /excuses/<id>
# ======================================================================

@excuse_bp.route("/<int:excuse_id>", methods=["DELETE"])
@role_required(Role.STUDENT)
def delete_excuse(excuse_id: int):
    excuse_service.delete_excuse(
        excuse_id=excuse_id,
        student_id=_current_student_id(),
        actor_id=g.user.id,
    )

    return jsonify({
        "message": (
            f"Excuse {excuse_id} "
            "deleted successfully."
        )
    }), 200


# ======================================================================
# POST /excuses/<id>/approve
# ======================================================================

@excuse_bp.route(
    "/<int:excuse_id>/approve",
    methods=["POST"],
)
@role_required(
    Role.ADMIN,
    Role.TEACHER,
)
def approve_excuse(excuse_id: int):
    excuse = excuse_service.approve_excuse(
        excuse_id=excuse_id,
        reviewer_id=g.user.id,
        actor_id=g.user.id,
    )

    return jsonify(
        _serialize_excuse(excuse)
    ), 200


# ======================================================================
# POST /excuses/<id>/reject
# ======================================================================

@excuse_bp.route(
    "/<int:excuse_id>/reject",
    methods=["POST"],
)
@role_required(
    Role.ADMIN,
    Role.TEACHER,
)
def reject_excuse(excuse_id: int):
    excuse = excuse_service.reject_excuse(
        excuse_id=excuse_id,
        reviewer_id=g.user.id,
        actor_id=g.user.id,
    )

    return jsonify(
        _serialize_excuse(excuse)
    ), 200


# ======================================================================
# POST /excuses/bulk-approve
# ======================================================================

@excuse_bp.route(
    "/bulk-approve",
    methods=["POST"],
)
@role_required(
    Role.ADMIN,
    Role.TEACHER,
)
def bulk_approve_excuses():
    try:
        data = BulkExcuseReviewRequest.model_validate(
            request.get_json() or {}
        )
    except ValidationError as err:
        return jsonify({
            "errors": err.errors()
        }), 400

    result = excuse_service.bulk_review_excuses(
        excuse_ids=data.excuse_ids,
        decision=ExcuseStatus.APPROVED,
        reviewer_id=g.user.id,
        actor_id=g.user.id,
    )

    return jsonify(result), 200


# ======================================================================
# POST /excuses/bulk-reject
# ======================================================================

@excuse_bp.route(
    "/bulk-reject",
    methods=["POST"],
)
@role_required(
    Role.ADMIN,
    Role.TEACHER,
)
def bulk_reject_excuses():
    try:
        data = BulkExcuseReviewRequest.model_validate(
            request.get_json() or {}
        )
    except ValidationError as err:
        return jsonify({
            "errors": err.errors()
        }), 400

    result = excuse_service.bulk_review_excuses(
        excuse_ids=data.excuse_ids,
        decision=ExcuseStatus.REJECTED,
        reviewer_id=g.user.id,
        actor_id=g.user.id,
    )

    return jsonify(result), 200