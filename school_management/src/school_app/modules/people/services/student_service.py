from flask import abort
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from school_app.models import Classroom

from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.user import User
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction
from school_app.modules.people.services.enrollment_service import record_enrollment

def create_students(form, school_id, actor_id=None):
    user = User(
        username=form.username,
        email=form.email,
        password=generate_password_hash(form.password),
        role="student",
        school_id=school_id,
    )
    db.session.add(user)

    try:  
        db.session.flush()

        student = Student(
            school_id=school_id,
            user_id=user.id,
            full_name=form.full_name,
            email=form.email,
            phone=form.phone,
            admission_number=form.admission_number,
            classroom_id=form.classroom_id,
        )
        db.session.add(student)
        db.session.flush() 

        if form.classroom_id is not None:
            record_enrollment(student.id, form.classroom_id, recorded_by=actor_id, school_id=school_id)
        
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create student — check for duplicate username, email, or admission number.")

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Student",
            resource_id=student.id,
            description=f"Created student {student.full_name}",
        )
    
    db.session.commit()
    
    return student


def get_all_students(school_id):
    return Student.query.filter(Student.school_id == school_id).order_by(Student.id.desc()).all()


def get_student_by_id(student_id, school_id):
    """Returns None both when the student doesn't exist AND when it exists
    but belongs to a different school — a route can't distinguish "not
    found" from "not yours" from the return value alone, which is the
    correct behavior here (confirming existence of another school's
    student via a different error shape is its own small leak)."""
    student = db.session.get(Student, student_id)
    if student is None or student.school_id != school_id:
        return None
    return student


def update_student(student_id, form, school_id, actor_id=None):
    student = get_student_by_id(student_id, school_id)
    if student is None:
        return None

    changes = {}
    if form.full_name and form.full_name != student.full_name:
        changes["full_name"] = {"before": student.full_name, "after": form.full_name}
    if form.email and form.email != student.email:
        changes["email"] = {"before": student.email, "after": form.email}
    if form.phone and form.phone != student.phone:
        changes["phone"] = {"before": student.phone, "after": form.phone}
    if form.admission_number and form.admission_number != student.admission_number:
        changes["admission_number"] = {"before": student.admission_number, "after": form.admission_number}
    if form.classroom_id is not None and form.classroom_id != student.classroom_id:
        changes["classroom_id"] = {"before": student.classroom_id, "after": form.classroom_id}

    if student.user is not None:
        student.user.email = form.email or student.user.email

    if form.classroom_id is not None and form.classroom_id != student.classroom_id:
        record_enrollment(student.id, form.classroom_id, recorded_by=actor_id, school_id=school_id)

    student.full_name = form.full_name or student.full_name
    student.email = form.email or student.email
    student.phone = form.phone or student.phone
    student.admission_number = form.admission_number or student.admission_number
    student.classroom_id = form.classroom_id if form.classroom_id is not None else student.classroom_id

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="That email is already in use.")

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Student",
            resource_id=student.id,
            description=f"Updated student {student.full_name}",
            changes=changes,
        )
        
    db.session.commit()

    return student


def delete_student(student_id, school_id, actor_id=None):
    student = get_student_by_id(student_id, school_id)
    if student is None:
        return False

    student_name = student.full_name
    user = student.user
    db.session.delete(student)
    if user is not None:
        db.session.delete(user)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Student",
            resource_id=student_id,
            description=f"Deleted student {student_name}",
        )
    
    db.session.commit()

    return True


def search_student_info(search, school_id):
    return (
        Student.query.join(Student.user)
        .filter(Student.school_id == school_id)
        .filter(or_(Student.full_name.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))
        .order_by(Student.id.desc())
        .all()
    )


def filter_classroom_id(classroom_id, school_id):
    return Student.query.filter(
        Student.classroom_id == classroom_id, Student.school_id == school_id
    ).order_by(Student.id.desc()).all()


def filter_admission_number(admission_number, school_id):
    return Student.query.filter(
        Student.admission_number == admission_number, Student.school_id == school_id
    ).order_by(Student.id.desc()).all()


def paginate_students(school_id, page=1, per_page=10):
    return Student.query.filter(Student.school_id == school_id).order_by(Student.id.desc()).paginate(page=page, per_page=per_page, error_out=False)


def sort_student(school_id, page=1, per_page=10):
    return Student.query.filter(Student.school_id == school_id).order_by(Student.id.desc()).paginate(page=page, per_page=per_page, error_out=False)


def add_student_to_classroom(student_id, classroom_id, school_id, actor_id=None):
    student = get_student_by_id(student_id, school_id)
    if student is None:
        return None

    classroom = db.session.get(Classroom, classroom_id)
    if classroom is None or classroom.school_id != school_id:
        abort(404, description="Classroom not found")

    record_enrollment(student_id, classroom_id, recorded_by=actor_id, school_id=school_id)
    student.classroom_id = classroom_id
    db.session.commit()
    return student


def delete_student_from_classroom(student_id, school_id, actor_id=None):
    student = get_student_by_id(student_id, school_id)
    if student is None:
        return None

    record_enrollment(student_id, None, recorded_by=actor_id, school_id=school_id)
    student.classroom_id = None
    db.session.commit()
    return student