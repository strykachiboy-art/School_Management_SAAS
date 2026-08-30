from flask import abort
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from school_app.extensions import db
from school_app.models.attendance import Attendance
from school_app.models.student import Student
from school_app.enums.attendance import AttendanceStatus
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


def _today():
    return datetime.now(timezone.utc).date()


def _assert_date_not_future(record_date, actor_role):
    """Block future-dated attendance unless a teacher is deliberately backfilling/exempting."""
    if record_date > _today() and actor_role != "teacher":
        abort(
            400,
            description=(
                "Attendance date cannot be in the future. "
                "Only a teacher can record attendance for a future date as an exception."
            ),
        )


# ============================ 1. Create Single Attendance ============================

def create_attendance(data, actor_role=None, actor_id=None):
    """
    Creates a single Attendance record.
    """
    _assert_date_not_future(data.date, actor_role)

    new_attendance = Attendance(
        student_id=data.student_id,
        term_id=data.term_id,
        date=data.date,
        status=data.status,
    )

    db.session.add(new_attendance)

    try:
        db.session.flush()  # Forces the SQL insert now so IntegrityError can be caught
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="Could not create attendance — duplicate student record on this date or missing required fields.",
        )

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Attendance",
            resource_id=new_attendance.id,
            description=f"Recorded attendance for student ID {new_attendance.student_id} on {new_attendance.date}",
        )
        
    db.session.commit()

    return new_attendance


# ============================ 2. Bulk Mark Classroom Attendance ============================

def mark_classroom_attendance(classroom_id, term_id, date, attendance_data, actor_role=None, actor_id=None):
    """
    Bulk creates or updates attendance records for a classroom on a specific date.
    """
    _assert_date_not_future(date, actor_role)

    try:
        # Fetch valid student IDs for this classroom
        classroom_students = Student.query.filter_by(classroom_id=classroom_id).all()
        valid_student_ids = {student.id for student in classroom_students}

        requested_student_ids = []
        for record in attendance_data:
            s_id = record["student_id"]
            if s_id not in valid_student_ids:
                abort(
                    400,
                    description=f"Student ID {s_id} does not belong to classroom {classroom_id}.",
                )
            requested_student_ids.append(s_id)

        # Fetch every existing record for this date/term in one query instead of
        # one query per student (avoids N+1 round-trips for large classrooms)
        existing_records = Attendance.query.filter(
            Attendance.student_id.in_(requested_student_ids),
            Attendance.term_id == term_id,
            Attendance.date == date,
        ).all()
        existing_by_student = {record.student_id: record for record in existing_records}

        new_records = []
        for record in attendance_data:
            s_id = record["student_id"]
            status = record["status"]

            existing = existing_by_student.get(s_id)
            if existing:
                # Update existing record
                existing.term_id = term_id
                existing.status = status
            else:
                # Queue for bulk insert
                new_records.append(
                    Attendance(
                        student_id=s_id,
                        term_id=term_id,
                        date=date,
                        status=status,
                    )
                )

        # Insert all new records in a single batched operation
        if new_records:
            db.session.bulk_save_objects(new_records)

        if actor_id:
            create_audit_log(
                actor_id=actor_id,
                action=AuditAction.UPDATE,
                resource_type="Classroom",
                resource_id=classroom_id,
                description=f"Bulk marked attendance for classroom ID {classroom_id} on {date}",
            )
            
            # Commit all changes at once (updates + bulk inserts)
            db.session.commit()

        return True

    except HTTPException:
        db.session.rollback()
        raise
    except Exception:
        db.session.rollback()
        raise


# ============================ 3. Get Attendance By ID ============================

def get_attendance_by_id(attendance_id):
    """
    Get a single attendance record by ID.
    """
    attendance = db.session.get(Attendance, attendance_id)
    if not attendance:
        abort(404, description=f"Attendance record with ID {attendance_id} not found.")
    return attendance


# ============================ 4. Get Student Attendance ============================

def get_student_attendance(student_id, term_id=None, start_date=None, end_date=None):
    """
    Get a student's attendance history, with optional filtering by term or date range.
    """
    query = Attendance.query.filter(Attendance.student_id == student_id)

    if term_id:
        query = query.filter(Attendance.term_id == term_id)
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)

    return query.order_by(Attendance.date.desc()).all()


# ============================ 5. Get Classroom Attendance ============================

def get_classroom_attendance(classroom_id, date=None, term_id=None):
    """
    Get attendance records for all students in a classroom for a given date or term.
    """
    query = Attendance.query.join(Student).filter(Student.classroom_id == classroom_id)

    if date:
        query = query.filter(Attendance.date == date)
    if term_id:
        query = query.filter(Attendance.term_id == term_id)

    return query.all()


# ============================ 6. Get Term Attendance ============================

def get_term_attendance(term_id):
    """
    Get all attendance records across a term.
    """
    return (
        Attendance.query.filter_by(term_id=term_id)
        .order_by(Attendance.date.desc())
        .all()
    )


# ============================ 7. Update Attendance ============================

def update_attendance(attendance_id, status=None, date=None, actor_id=None):
    """
    Correct/update an existing attendance record.
    """
    attendance = get_attendance_by_id(attendance_id)

    changes = {}
    if status is not None and status != attendance.status:
        changes["status"] = {"before": str(attendance.status), "after": str(status)}
    if date is not None and date != attendance.date:
        changes["date"] = {"before": str(attendance.date), "after": str(date)}

    if status is not None:
        attendance.status = status
    if date is not None:
        attendance.date = date

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(
            400,
            description="Could not update attendance — duplicate record found for this student and date.",
        )

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Attendance",
            resource_id=attendance.id,
            description=f"Updated attendance record for student ID {attendance.student_id}",
            changes=changes,
        )
        
        db.session.commit()

    return attendance


# ============================ 8. Delete Attendance ============================

def delete_attendance(attendance_id, actor_id=None):
    """
    Remove an attendance record if entered incorrectly.
    """
    attendance = get_attendance_by_id(attendance_id)
    student_id = attendance.student_id
    att_date = attendance.date

    db.session.delete(attendance)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Attendance",
            resource_id=attendance_id,
            description=f"Deleted attendance record for student ID {student_id} on {att_date}",
        )
        
        db.session.commit()

    return True


# ============================ 9. Get Attendance Summary ============================

def get_attendance_summary(student_id, term_id=None):
    """
    Calculate summary statistics (total, status counts, percentage) for a student.
    """
    query = Attendance.query.filter(Attendance.student_id == student_id)
    if term_id:
        query = query.filter(Attendance.term_id == term_id)

    records = query.all()
    total_days = len(records)

    if total_days == 0:
        return {
            "total_school_days": 0,
            "present": 0,
            "absent": 0,
            "late": 0,
            "excused": 0,
            "attendance_percentage": 0.0,
        }

    present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
    absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
    excused = sum(1 for r in records if r.status == AttendanceStatus.EXCUSED)

    attended_days = present + late
    attendance_percentage = round((attended_days / total_days) * 100, 2)

    return {
        "total_school_days": total_days,
        "present": present,
        "absent": absent,
        "late": late,
        "excused": excused,
        "attendance_percentage": attendance_percentage,
    }