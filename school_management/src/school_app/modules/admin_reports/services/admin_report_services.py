from decimal import Decimal
from sqlalchemy import select, func

from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.teacher import Teacher
from school_app.models.subject import Subject
from school_app.models.classroom import Classroom
from school_app.models.attendance import Attendance
from school_app.enums.attendance import AttendanceStatus
from school_app.models.school_fees import Invoice
from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term


def get_admin_report_overview():
    total_students = db.session.scalar(select(func.count()).select_from(Student))
    total_teachers = db.session.scalar(select(func.count()).select_from(Teacher))
    total_subjects = db.session.scalar(select(func.count()).select_from(Subject))
    total_classrooms = db.session.scalar(select(func.count()).select_from(Classroom))

    active_session = db.session.scalar(
        select(AcademicSession).where(AcademicSession.is_active.is_(True))
    )
    active_term = db.session.scalar(
        select(Term).where(Term.is_current.is_(True))
    )
    total_attendance_records = db.session.scalar(select(func.count()).select_from(Attendance))
    present_count = db.session.scalar(
        select(func.count()).select_from(Attendance).where(Attendance.status == AttendanceStatus.PRESENT)
    )
    attendance_rate = (
        round((present_count / total_attendance_records) * 100, 1)
        if total_attendance_records
        else None
    )

    total_expected = db.session.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount - Invoice.discount_amount - Invoice.waived_amount), Decimal("0.00")))
    )
    total_paid = db.session.scalar(
        select(func.coalesce(func.sum(Invoice.amount_paid), Decimal("0.00")))
    )
    outstanding_balance = total_expected - total_paid
    collection_rate = (
        round(float(total_paid) / float(total_expected) * 100, 1)
        if total_expected
        else None
    )

    return {
        "students": {"total": total_students},
        "teachers": {"total": total_teachers},
        "subjects": {"total": total_subjects},
        "classrooms": {"total": total_classrooms},
        "attendance": {
            "total_records": total_attendance_records,
            "attendance_rate": attendance_rate,
        },
        "fees": {
            "total_expected": float(total_expected),
            "total_paid": float(total_paid),
            "outstanding_balance": float(outstanding_balance),
            "collection_rate": collection_rate,
        },
        "system": {
            "active_session": active_session.name if active_session else None,
            "active_term": active_term.name if active_term else None,
        },
    }