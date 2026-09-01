from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required

from school_app.decorators import role_required
from school_app.enums.role import Role

from school_app.modules.classrooms.services.timetable_service import (
    create_timetable,
    get_timetable,
    get_timetables,
    update_timetable,
    delete_timetable,
    get_teacher_timetable,
    get_classroom_timetable,
)

from school_app.modules.classrooms.requests.timetable_request import (
    TimetableCreateRequest,
    TimetableUpdateRequest,
)


timetable_bp = Blueprint(
    "timetable_bp",
    __name__,
    url_prefix="/timetables",
)


def _serialize_timetable(t):
    return {
        "id": t.id,
        "school_id": t.school_id,
        "term_id": t.term_id,
        "classroom_id": t.classroom_id,
        "subject_id": t.subject_id,
        "teacher_id": t.teacher_id,
        "day_of_week": (
            t.day_of_week.name
            if hasattr(t.day_of_week, "name")
            else t.day_of_week
        ),
        "start_time": t.start_time.isoformat() if t.start_time else None,
        "end_time": t.end_time.isoformat() if t.end_time else None,
    }


# ====================================== create_timetable ===============================================

@timetable_bp.route("", methods=["POST"])
@jwt_required()
@role_required(Role.ADMIN)
def create_timetable_route():
    json_data = request.get_json() or {}

    try:
        payload = TimetableCreateRequest(**json_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    timetable = create_timetable(
        payload.model_dump(),
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    return jsonify({
        "message": "Timetable entry created successfully.",
        "data": _serialize_timetable(timetable),
    }), 201


# ====================================== get_timetable ===============================================

@timetable_bp.route("/<int:timetable_id>", methods=["GET"])
@jwt_required()
@role_required(Role.ADMIN)
def get_timetable_route(timetable_id):
    timetable = get_timetable(
        timetable_id,
        school_id=g.user.school_id,
    )

    return jsonify(_serialize_timetable(timetable)), 200


# ====================================== get_timetables ===============================================

@timetable_bp.route("", methods=["GET"])
@jwt_required()
@role_required(Role.ADMIN)
def get_timetables_route():
    school_id = g.user.school_id

    search = request.args.get("search", "")
    term_id = request.args.get("term_id", type=int)
    classroom_id = request.args.get("classroom_id", type=int)
    teacher_id = request.args.get("teacher_id", type=int)
    day_of_week = request.args.get("day_of_week")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    pagination = get_timetables(
        school_id=school_id,
        search=search,
        term_id=term_id,
        classroom_id=classroom_id,
        teacher_id=teacher_id,
        day_of_week=day_of_week,
        page=page,
        per_page=per_page,
    )

    return jsonify({
        "items": [
            _serialize_timetable(t)
            for t in pagination.items
        ],
        "total": pagination.total,
        "pages": pagination.pages,
        "page": pagination.page,
        "per_page": per_page,
    }), 200


# ====================================== update_timetable ===============================================

@timetable_bp.route("/<int:timetable_id>", methods=["PUT"])
@jwt_required()
@role_required(Role.ADMIN)
def update_timetable_route(timetable_id):
    json_data = request.get_json() or {}

    try:
        payload = TimetableUpdateRequest(**json_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 422

    update_data = payload.model_dump(exclude_unset=True)

    timetable = update_timetable(
        timetable_id,
        update_data,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    return jsonify({
        "message": "Timetable entry updated successfully.",
        "data": _serialize_timetable(timetable),
    }), 200


# ====================================== delete_timetable ===============================================

@timetable_bp.route("/<int:timetable_id>", methods=["DELETE"])
@jwt_required()
@role_required(Role.ADMIN)
def delete_timetable_route(timetable_id):
    delete_timetable(
        timetable_id,
        school_id=g.user.school_id,
        actor_id=g.user.id,
    )

    return jsonify({
        "message": "Timetable entry deleted successfully."
    }), 200


# ====================================== get_teacher_timetable ===============================================

@timetable_bp.route("/teacher/<int:teacher_id>", methods=["GET"])
@jwt_required()
@role_required(Role.ADMIN, Role.TEACHER)
def get_teacher_timetable_route(teacher_id):
    term_id = request.args.get("term_id", type=int)
    day_of_week = request.args.get("day_of_week")

    timetables = get_teacher_timetable(
        teacher_id,
        school_id=g.user.school_id,
        term_id=term_id,
        day_of_week=day_of_week,
    )

    return jsonify([
        _serialize_timetable(t)
        for t in timetables
    ]), 200


# ====================================== get_classroom_timetable ===============================================

@timetable_bp.route("/classroom/<int:classroom_id>", methods=["GET"])
@jwt_required()
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_classroom_timetable_route(classroom_id):
    term_id = request.args.get("term_id", type=int)
    day_of_week = request.args.get("day_of_week")

    timetables = get_classroom_timetable(
        classroom_id,
        school_id=g.user.school_id,
        term_id=term_id,
        day_of_week=day_of_week,
    )

    return jsonify([
        _serialize_timetable(t)
        for t in timetables
    ]), 200