from flask import Blueprint, jsonify, request, g, abort
from pydantic import ValidationError

# Import your role-required decorator and the new Role enum
from school_app.decorators import role_required
from school_app.enums.role import Role

from school_app.modules.people.requests.parent_guardian_request import (
    ParentGuardianCreateRequest,
    ParentGuardianUpdateRequest
)
from school_app.modules.people.requests.parent_guardian_student_request import (
    ParentGuardianStudentCreateRequest,
    ParentGuardianStudentUpdateRequest
)

from school_app.modules.people.services.parent_guardian_service import (
    create_parent_guardian,
    get_parent_guardian,
    get_all_parent_guardians,
    update_parent_guardian,
    delete_parent_guardian,
    assign_student_to_guardian,
    get_guardian_students,
    get_student_guardians,
    update_guardian_student_relationship,
    remove_student_from_guardian
)

parent_guardian_bp = Blueprint("parent_guardian", __name__, url_prefix="/parent-guardians")

# ==========================================
# Parent Guardian Endpoints
# ==========================================

@parent_guardian_bp.route("", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
def create_guardian():
    try:
        body = request.get_json()
        validated_data = ParentGuardianCreateRequest(**body)
        
        guardian = create_parent_guardian(validated_data.model_dump(), actor_id=g.user.id)
        return jsonify({
            "message": "Parent/Guardian created successfully",
            "id": guardian.id,
            "user_id": guardian.user_id,
            "occupation": guardian.occupation,
            "email": guardian.email,
            "phone": guardian.phone,
            "address": guardian.address
        }), 201
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@parent_guardian_bp.route("", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def list_guardians():
    guardians = get_all_parent_guardians()
    result = [{
        "id": g.id,
        "user_id": g.user_id,
        "occupation": g.occupation,
        "email": g.email,
        "phone": g.phone,
        "address": g.address
    } for g in guardians]
    return jsonify(result), 200


@parent_guardian_bp.route("/<int:guardian_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.PARENT)
def get_guardian(guardian_id):
    guardian = get_parent_guardian(guardian_id)
    if not guardian:
        return jsonify({"error": "Parent/Guardian not found"}), 404
    return jsonify({
        "id": guardian.id,
        "user_id": guardian.user_id,
        "occupation": guardian.occupation,
        "email": guardian.email,
        "phone": guardian.phone,
        "address": guardian.address
    }), 200


@parent_guardian_bp.route("/<int:guardian_id>", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN, Role.TEACHER)
def update_guardian(guardian_id):
    try:
        body = request.get_json()
        validated_data = ParentGuardianUpdateRequest(**body)
        
        updated = update_parent_guardian(guardian_id, validated_data.model_dump(exclude_unset=True), actor_id=g.user.id)
        if not updated:
            return jsonify({"error": "Parent/Guardian not found"}), 404
            
        return jsonify({"message": "Parent/Guardian updated successfully"}), 200
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@parent_guardian_bp.route("/<int:guardian_id>", methods=["DELETE"])
@role_required(Role.ADMIN)
def delete_guardian(guardian_id):
    success = delete_parent_guardian(guardian_id, actor_id=g.user.id)
    if not success:
        return jsonify({"error": "Parent/Guardian not found"}), 404
    return jsonify({"message": "Parent/Guardian deleted successfully"}), 200


# ==========================================
# Parent Guardian Student Assignment Endpoints
# ==========================================

@parent_guardian_bp.route("/students", methods=["POST"])
@role_required(Role.ADMIN, Role.TEACHER)
def assign_student():
    try:
        body = request.get_json()
        validated_data = ParentGuardianStudentCreateRequest(**body)
        
        assignment = assign_student_to_guardian(validated_data.model_dump(), actor_id=g.user.id)
        return jsonify({
            "message": "Student assigned to guardian successfully",
            "id": assignment.id,
            "parent_guardian_id": assignment.parent_guardian_id,
            "student_id": assignment.student_id,
            "relationship": assignment.relationship.value
        }), 201
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@parent_guardian_bp.route("/<int:guardian_id>/students", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.PARENT)
def get_students_for_guardian(guardian_id):
    assignments = get_guardian_students(guardian_id)
    result = [{
        "id": a.id,
        "student_id": a.student_id,
        "relationship": a.relationship.value
    } for a in assignments]
    return jsonify(result), 200


@parent_guardian_bp.route("/students/assignments/<int:record_id>", methods=["DELETE"])
@role_required(Role.ADMIN, Role.TEACHER)
def remove_student_assignment(record_id):
    success = remove_student_from_guardian(record_id, actor_id=g.user.id)
    if not success:
        return jsonify({"error": "Assignment not found"}), 404
    return jsonify({"message": "Student unlinked from guardian successfully"}), 200