from flask import Blueprint, jsonify, request, g, abort
from pydantic import ValidationError
from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.models.parent_guardian import ParentGuardian, ParentGuardianStudent

attendance_bp = Blueprint("attendance", __name__, url_prefix="/attendances")


def _parent_owns_student(user_id: int, student_id: int) -> bool:
    """Check the current parent/guardian is actually linked to this student."""
    guardian = ParentGuardian.query.filter_by(user_id=user_id).first()
    if not guardian:
        return False
    link = ParentGuardianStudent.query.filter_by(
        parent_guardian_id=guardian.id, student_id=student_id
    ).first()
    return link is not None


def _enforce_attendance_ownership(student_id: int):
    """Abort 403 if the caller is a student/parent without a claim on this student_id."""
    if g.user.role == Role.STUDENT:
        if getattr(g.user.student_profile, "id", None) != student_id:
            abort(403, description="You can only view your own attendance.")
    elif g.user.role == Role.PARENT:
        if not _parent_owns_student(g.user.id, student_id):
            abort(403, description="You can only view your own child's attendance.")

from school_app.modules.attendance.requests.attendance_request import (
    AttendanceCreateRequest,
    AttendanceUpdateRequest,
    AttendanceResponse,
    MarkClassroomAttendanceRequest,
)

# Alias the imported service functions to prevent name collisions
from school_app.modules.attendance.services.attendance_service import (
    create_attendance as create_attendance_service,
    get_attendance_by_id as get_attendance_by_id_service,
    get_student_attendance as get_student_attendance_service,
    get_classroom_attendance as get_classroom_attendance_service,
    get_term_attendance as get_term_attendance_service,
    update_attendance as update_attendance_service,
    delete_attendance as delete_attendance_service,
    get_attendance_summary as get_attendance_summary_service,
    mark_classroom_attendance as mark_classroom_attendance_service,
)


# Helper function for serializing response objects or lists via Pydantic
def serialize_attendance(attendance):
    if isinstance(attendance, list):
        return [
            AttendanceResponse.model_validate(item).model_dump(mode="json")
            for item in attendance
        ]
    return AttendanceResponse.model_validate(attendance).model_dump(mode="json")


# ============================ 1. Create Single Attendance ============================

@attendance_bp.route("", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
def create_attendance():
    try:
        data = AttendanceCreateRequest.model_validate(request.json)
    except ValidationError as err:
        return jsonify(err.errors()), 422

    record = create_attendance_service(data, actor_id=g.user.id)
    return jsonify(serialize_attendance(record)), 201


# ============================ 2. Mark Classroom Attendance (Bulk) ============================

@attendance_bp.route("/classrooms/<int:classroom_id>/mark", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
def mark_classroom_attendance(classroom_id: int):
    try:
        payload = MarkClassroomAttendanceRequest.model_validate(request.json)
    except ValidationError as err:
        return jsonify(err.errors()), 422

    records = [record.model_dump() for record in payload.attendance_data]

    mark_classroom_attendance_service(
        classroom_id=classroom_id,
        term_id=payload.term_id,
        date=payload.date,
        attendance_data=records,
        actor_id=g.user.id,
    )

    return jsonify({"message": "Classroom attendance marked successfully."}), 200


# ============================ 3. Get Single Attendance ============================

@attendance_bp.route("/<int:attendance_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT, Role.PARENT)
def get_attendance_by_id(attendance_id: int):
    record = get_attendance_by_id_service(attendance_id)
    if record is None:
        abort(404, description="Attendance record not found")
    _enforce_attendance_ownership(record.student_id)
    return jsonify(serialize_attendance(record)), 200


# ============================ 4. Get Student Attendance History ============================

@attendance_bp.route("/students/<int:student_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT, Role.PARENT)
def get_student_attendance(student_id: int):
    _enforce_attendance_ownership(student_id)
    term_id = request.args.get("term_id", type=int)
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    records = get_student_attendance_service(
        student_id=student_id,
        term_id=term_id,
        start_date=start_date,
        end_date=end_date,
    )
    return jsonify(serialize_attendance(records)), 200


# ============================ 5. Get Classroom Attendance ============================

@attendance_bp.route("/classrooms/<int:classroom_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_classroom_attendance(classroom_id: int):
    date_val = request.args.get("date")
    term_id = request.args.get("term_id", type=int)

    records = get_classroom_attendance_service(
        classroom_id=classroom_id,
        date=date_val,
        term_id=term_id,
    )
    return jsonify(serialize_attendance(records)), 200


# ============================ 6. Get Term Attendance ============================

@attendance_bp.route("/terms/<int:term_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_term_attendance(term_id: int):
    records = get_term_attendance_service(term_id)
    return jsonify(serialize_attendance(records)), 200


# ============================ 7. Update Attendance ============================

@attendance_bp.route("/<int:attendance_id>", methods=["PATCH"])
@role_required(Role.ADMIN, Role.TEACHER)
def update_attendance(attendance_id: int):
    try:
        data = AttendanceUpdateRequest.model_validate(request.json)
    except ValidationError as err:
        return jsonify(err.errors()), 422

    record = update_attendance_service(
        attendance_id=attendance_id,
        status=data.status,
        date=data.date,
        actor_id=g.user.id,
    )
    return jsonify(serialize_attendance(record)), 200


# ============================ 8. Delete Attendance ============================

@attendance_bp.route("/<int:attendance_id>", methods=["DELETE"])
@role_required(Role.ADMIN, Role.TEACHER)
def delete_attendance(attendance_id: int):
    deleted = delete_attendance_service(attendance_id, actor_id=g.user.id)
    if not deleted:
        abort(404, description="Attendance record not found")
    return jsonify({"message": f"Attendance record {attendance_id} deleted successfully."}), 200


# ============================ 9. Get Attendance Summary ============================

@attendance_bp.route("/students/<int:student_id>/summary", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT, Role.PARENT)
def get_attendance_summary(student_id: int):
    _enforce_attendance_ownership(student_id)
    term_id = request.args.get("term_id", type=int)
    summary = get_attendance_summary_service(
        student_id=student_id, term_id=term_id
    )
    return jsonify(summary), 200