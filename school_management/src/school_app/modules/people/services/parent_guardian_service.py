from school_app.extensions import db
from school_app.models.parent_guardian import ParentGuardian, ParentGuardianStudent
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction

# ==========================================
# Parent Guardian Services
# ==========================================

def create_parent_guardian(data: dict, actor_id=None):
    new_guardian = ParentGuardian(
        user_id=data.get("user_id"),
        occupation=data.get("occupation"),
        email=data.get("email"),
        phone=data.get("phone"),
        address=data.get("address")
    )
    db.session.add(new_guardian)
    db.session.flush()  # Ensure ID is populated for the audit log

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="ParentGuardian",
            resource_id=new_guardian.id,
            description=f"Created parent/guardian profile for user ID {new_guardian.user_id}",
        )
        
    db.session.commit()

    return new_guardian


def get_parent_guardian(guardian_id: int):
    return db.session.get(ParentGuardian, guardian_id)


def get_all_parent_guardians():
    return ParentGuardian.query.all()


def update_parent_guardian(guardian_id: int, data: dict, actor_id=None):
    guardian = get_parent_guardian(guardian_id)
    if not guardian:
        return None
    
    changes = {}
    for key, value in data.items():
        if value is not None:
            old_val = getattr(guardian, key, None)
            if old_val != value:
                changes[key] = {"before": old_val, "after": value}
            setattr(guardian, key, value)
            
    db.session.flush()

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="ParentGuardian",
            resource_id=guardian.id,
            description=f"Updated parent/guardian ID {guardian.id}",
            changes=changes,
        )
        
    db.session.commit()

    return guardian


def delete_parent_guardian(guardian_id: int, actor_id=None):
    guardian = get_parent_guardian(guardian_id)
    if not guardian:
        return False
        
    db.session.delete(guardian)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="ParentGuardian",
            resource_id=guardian_id,
            description=f"Deleted parent/guardian ID {guardian_id}",
        )
        
    db.session.commit()

    return True


# ==========================================
# Parent Guardian Student Services
# ==========================================

def assign_student_to_guardian(data: dict, actor_id=None):
    assignment = ParentGuardianStudent(
        parent_guardian_id=data.get("parent_guardian_id"),
        student_id=data.get("student_id"),
        relationship=data.get("relationship")
    )
    db.session.add(assignment)
    db.session.flush()  # Ensure ID is populated for the audit log

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="ParentGuardianStudent",
            resource_id=assignment.id,
            description=f"Assigned student ID {assignment.student_id} to parent/guardian ID {assignment.parent_guardian_id}",
        )
        
    db.session.commit()

    return assignment


def get_guardian_students(guardian_id: int):
    return ParentGuardianStudent.query.filter_by(parent_guardian_id=guardian_id).all()


def get_student_guardians(student_id: int):
    return ParentGuardianStudent.query.filter_by(student_id=student_id).all()


def update_guardian_student_relationship(record_id: int, data: dict, actor_id=None):
    assignment = db.session.get(ParentGuardianStudent, record_id)
    if not assignment:
        return None
        
    changes = {}
    for key, value in data.items():
        if value is not None:
            old_val = getattr(assignment, key, None)
            if old_val != value:
                changes[key] = {"before": old_val, "after": value}
            setattr(assignment, key, value)
            
    db.session.flush()

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="ParentGuardianStudent",
            resource_id=assignment.id,
            description=f"Updated relationship record ID {assignment.id}",
            changes=changes,
        )
        
    db.session.commit()

    return assignment


def remove_student_from_guardian(record_id: int, actor_id=None):
    assignment = db.session.get(ParentGuardianStudent, record_id)
    if not assignment:
        return False
        
    p_id = assignment.parent_guardian_id
    s_id = assignment.student_id
    
    db.session.delete(assignment)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="ParentGuardianStudent",
            resource_id=record_id,
            description=f"Removed student ID {s_id} from parent/guardian ID {p_id}",
        )
        
    db.session.commit()

    return True