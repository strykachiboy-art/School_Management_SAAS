from flask import Blueprint, jsonify, abort, g

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.enums.permission import Permission
from school_app.extensions import db
from school_app.models.teacher import Teacher
from school_app.utils.helpers import validate_request

from school_app.modules.people.requests.teacher_permission_request import (
    AssignPermissionRequest,
    UpdatePermissionsRequest,
    TeacherPermissionResponse,
)

from school_app.modules.people.services.teacher_permission_service import (
    assign_teacher_permission,
    get_teacher_permissions,
    get_all_teacher_permissions,
    update_teacher_permissions,
    remove_teacher_permission,
)


teacher_permission_bp = Blueprint(
    "teacher_permission",
    __name__,
    url_prefix="/admin/teachers",
)


def _serialize(record):
    return TeacherPermissionResponse.model_validate(record).model_dump(mode="json")


def _get_teacher_school_id(teacher_id: int) -> int:
    teacher = db.session.get(Teacher, teacher_id)

    if teacher is None:
        abort(404, description=f"Teacher with ID {teacher_id} not found.")

    return teacher.school_id


# ====================================== assign ======================================

@teacher_permission_bp.route(
    "/<int:teacher_id>/permissions",
    methods=["POST"],
)
@role_required(Role.ADMIN)
@validate_request(AssignPermissionRequest)
def assign_permission_route(data: AssignPermissionRequest, teacher_id):
    school_id = _get_teacher_school_id(teacher_id)

    record = assign_teacher_permission(
        teacher_id,
        data.permission,
        school_id,
        actor_id=g.user.id,
    )

    return jsonify({
        "message": "Permission assigned successfully.",
        "data": _serialize(record),
    }), 201


# ====================================== get teacher permissions ======================================

@teacher_permission_bp.route(
    "/<int:teacher_id>/permissions",
    methods=["GET"],
)
@role_required(Role.ADMIN)
def get_teacher_permissions_route(teacher_id):
    school_id = _get_teacher_school_id(teacher_id)

    records = get_teacher_permissions(
        teacher_id,
        school_id,
    )

    return jsonify([_serialize(r) for r in records]), 200


# ====================================== update ======================================

@teacher_permission_bp.route(
    "/<int:teacher_id>/permissions",
    methods=["PUT"],
)
@role_required(Role.ADMIN)
@validate_request(UpdatePermissionsRequest)
def update_permissions_route(data: UpdatePermissionsRequest, teacher_id):
    school_id = _get_teacher_school_id(teacher_id)

    records = update_teacher_permissions(
        teacher_id,
        data.permissions,
        school_id,
        actor_id=g.user.id,
    )

    return jsonify({
        "message": "Permissions updated successfully.",
        "data": [_serialize(r) for r in records],
    }), 200


# ====================================== remove ======================================

@teacher_permission_bp.route(
    "/<int:teacher_id>/permissions/<string:permission_value>",
    methods=["DELETE"],
)
@role_required(Role.ADMIN)
def remove_permission_route(teacher_id, permission_value):
    try:
        permission = Permission(permission_value)
    except ValueError:
        abort(
            400,
            description=f"'{permission_value}' is not a valid permission.",
        )

    school_id = _get_teacher_school_id(teacher_id)

    remove_teacher_permission(
        teacher_id,
        permission,
        school_id,
        actor_id=g.user.id,
    )

    return jsonify({
        "message": "Permission removed successfully."
    }), 200


# ====================================== get all ======================================

@teacher_permission_bp.route(
    "/permissions",
    methods=["GET"],
)
@role_required(Role.ADMIN)
def get_all_permissions_route():
    
    school_id = g.user.school_id

    records = get_all_teacher_permissions(school_id)

    return jsonify([_serialize(r) for r in records]), 200
