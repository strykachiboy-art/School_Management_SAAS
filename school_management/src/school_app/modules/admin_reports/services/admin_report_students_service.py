from collections import defaultdict
from sqlalchemy import select

from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term
from school_app.models.result import Result
from school_app.models.exam import Exam
from school_app.models.attendance import Attendance
from school_app.enums.attendance import AttendanceStatus
from school_app.models.school_fees import Invoice
from school_app.enums.school_fees import InvoiceStatus
from school_app.modules.grading.services.grade_service import calculate_grade

OUTSTANDING_STATUSES = {InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE}


def _fees_status_for_student(invoices):
    if not invoices:
        return "no_fees_on_record"
    if any(inv.status in OUTSTANDING_STATUSES for inv in invoices):
        return "outstanding"
    return "paid_up"


def get_admin_report_students(classroom_id=None, gender=None, session_id=None,
                               term_id=None, is_active=None, start_date=None, end_date=None,
                               page=1, page_size=50):
    query = select(Student)
    if classroom_id is not None:
        query = query.where(Student.classroom_id == classroom_id)
    if gender is not None:
        query = query.where(Student.gender == gender)
    if session_id is not None:
        query = query.where(Student.current_session_id == session_id)
    if term_id is not None:
        query = query.where(Student.current_term_id == term_id)
    if is_active is not None:
        query = query.where(Student.is_active == is_active)
    if start_date is not None:
        query = query.where(Student.created_at >= start_date)
    if end_date is not None:
        query = query.where(Student.created_at <= end_date)

    students = db.session.execute(query).scalars().all()
    total_students = len(students)

    active_count = sum(1 for s in students if s.is_active)
    inactive_count = total_students - active_count

    by_gender = defaultdict(int)
    for s in students:
        by_gender[s.gender or "unspecified"] += 1

    classroom_ids = {s.classroom_id for s in students if s.classroom_id is not None}
    classroom_names = {
        c.id: c.name for c in db.session.execute(
            select(Classroom).where(Classroom.id.in_(classroom_ids))
        ).scalars().all()
    } if classroom_ids else {}

    by_classroom = defaultdict(int)
    for s in students:
        by_classroom[s.classroom_id] += 1
    by_classroom_report = [
        {
            "classroom_id": cid,
            "classroom_name": classroom_names.get(cid, "Unknown") if cid else "Unassigned",
            "count": count,
        }
        for cid, count in by_classroom.items()
    ]
    by_classroom_report.sort(key=lambda c: c["classroom_name"])

    session_ids = {s.current_session_id for s in students if s.current_session_id is not None}
    session_names = {
        sess.id: sess.name for sess in db.session.execute(
            select(AcademicSession).where(AcademicSession.id.in_(session_ids))
        ).scalars().all()
    } if session_ids else {}
    by_session = defaultdict(int)
    for s in students:
        by_session[s.current_session_id] += 1
    by_session_report = [
        {
            "session_id": sid,
            "session_name": session_names.get(sid, "Unknown") if sid else "Unassigned",
            "count": count,
        }
        for sid, count in by_session.items()
    ]
    by_session_report.sort(key=lambda s: s["session_name"])

    term_ids = {s.current_term_id for s in students if s.current_term_id is not None}
    term_names = {
        t.id: t.name for t in db.session.execute(
            select(Term).where(Term.id.in_(term_ids))
        ).scalars().all()
    } if term_ids else {}
    by_term = defaultdict(int)
    for s in students:
        by_term[s.current_term_id] += 1
    by_term_report = [
        {
            "term_id": tid,
            "term_name": term_names.get(tid, "Unknown") if tid else "Unassigned",
            "count": count,
        }
        for tid, count in by_term.items()
    ]
    by_term_report.sort(key=lambda t: t["term_name"])

    # ---- Per-student summary row ----
    # Sort + paginate the STUDENT ROWS first, then only run the three
    # expensive per-student sub-queries (academic/attendance/fees) on
    # the current page. Aggregates above (total_students, by_gender,
    # etc.) already reflect the full filtered set — only this detailed
    # list is capped, and capped BEFORE the expensive lookups run, not
    # just at serialization time.
    students_sorted = sorted(students, key=lambda s: s.full_name)
    total_students_matched = len(students_sorted)
    start = (page - 1) * page_size
    page_of_students = students_sorted[start:start + page_size]

    students_report = []
    for s in page_of_students:
        academic_query = (
            select(Result.marks_obtained)
            .join(Exam, Result.exam_id == Exam.id)
            .where(Result.student_id == s.id)
        )
        if session_id is not None:
            academic_query = academic_query.where(Exam.session_id == session_id)
        marks = db.session.execute(academic_query).scalars().all()
        average = round(sum(marks) / len(marks), 2) if marks else None
        grade = calculate_grade(average) if average is not None else None

        attendance_query = select(Attendance.status).where(Attendance.student_id == s.id)
        if term_id is not None:
            attendance_query = attendance_query.where(Attendance.term_id == term_id)
        statuses = db.session.execute(attendance_query).scalars().all()
        attendance_rate = (
            round(sum(1 for st in statuses if st == AttendanceStatus.PRESENT) / len(statuses) * 100, 1)
            if statuses else None
        )

        invoice_query = select(Invoice).where(Invoice.student_id == s.id)
        if session_id is not None:
            invoice_query = invoice_query.where(Invoice.session_id == session_id)
        invoices = db.session.execute(invoice_query).scalars().all()
        fees_status = _fees_status_for_student(invoices)

        students_report.append({
            "student_id": s.id,
            "full_name": s.full_name,
            "admission_number": s.admission_number,
            "classroom_id": s.classroom_id,
            "classroom_name": classroom_names.get(s.classroom_id, "Unknown") if s.classroom_id else "Unassigned",
            "gender": s.gender,
            "is_active": s.is_active,
            "current_session_name": session_names.get(s.current_session_id) if s.current_session_id else None,
            "current_term_name": term_names.get(s.current_term_id) if s.current_term_id else None,
            "academic_average": average,
            "grade": grade,
            "attendance_rate": attendance_rate,
            "fees_status": fees_status,
        })

    return {
        "total_students": total_students,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "by_gender": dict(by_gender),
        "by_classroom": by_classroom_report,
        "by_session": by_session_report,
        "by_term": by_term_report,
        "students": students_report,
        "students_pagination": {
            "page": page,
            "page_size": page_size,
            "total_students": total_students_matched,
            "total_pages": (total_students_matched + page_size - 1) // page_size if total_students_matched else 0,
        },
    }