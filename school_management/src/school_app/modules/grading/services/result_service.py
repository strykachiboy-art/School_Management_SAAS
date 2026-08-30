from flask import abort, request
from school_app.models.result import Result
from school_app.models.student import Student
from school_app.models.exam import Exam
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ========================== Create Result ============================
def create_result(student_id, exam_id, marks_obtained, actor_id=None):
    student = db.session.get(Student, student_id)
    if student is None:
        abort(404, description="Student not found")

    exam = db.session.get(Exam, exam_id)
    if exam is None:
        abort(404, description="Exam not found")

    result = Result(
        student_id=student_id,
        exam_id=exam_id,
        marks_obtained=marks_obtained
    )
    db.session.add(result)

    if actor_id:
        # Flush to get the result.id before logging
        db.session.flush() 
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Result",
            resource_id=result.id,
            description=f"Created result for student ID {student_id} in exam ID {exam_id}",
        )

    db.session.commit()
    return result


#================================ Get Result ==================================
def get_result(result_id):
    return db.session.get(Result, result_id)


#=============================== Get all Result ===============================
def get_all_result():
    return db.session.execute(
        db.select(Result)
    ).scalars().all()
    
    
#============================== Update Result ====================================
def update_result(result_id, mark_obtained, actor_id=None):
    result = db.session.get(Result, result_id)
    
    if result is None:
        abort(404, description = "Result does not exist")
    
    old_marks = result.marks_obtained
    changes = {}
    if mark_obtained is not None and mark_obtained != old_marks:
        changes["marks_obtained"] = {"before": old_marks, "after": mark_obtained}
    
    result.marks_obtained = mark_obtained
    db.session.flush()
    
    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Result",
            resource_id=result.id,
            description=f"Updated result ID {result.id} marks obtained",
            changes=changes,
        )
        
        db.session.commit()
    
    return result


# ============================= Delete result =====================================
def delete_result(result_id, actor_id=None):
    result = db.session.get(Result, result_id)
    
    if result is None:
       abort(404, description = "Result does not exist")
       
    student_id = result.student_id
    exam_id = result.exam_id
       
    db.session.delete(result)
    
    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Result",
            resource_id=result_id,
            description=f"Deleted result ID {result_id} for student ID {student_id}, exam ID {exam_id}",
        )
        
        db.session.commit()
    
    return result


#=========================== Search_result =====================================
def search_results(student_id = None, exam_id= None):
    statement = db.select(Result)
    
    if student_id is not None:
        statement = statement.where(
            Result.student_id == student_id
        )
    
    if exam_id is not None:
        statement = statement.where(
            Result.exam_id == exam_id
        )
    
    return db.session.execute(statement).scalars().all()


# =========================== Paginate_Result ===================================
def paginate_result(page = 1, per_page = 10):
    statement = db.select(Result)
    
    return db.paginate(statement,
                       page=page,
                       per_page=per_page,
                       error_out=False)