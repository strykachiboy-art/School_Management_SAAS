from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select, func

from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term
from school_app.models.result import Result
from school_app.models.exam import Exam
from school_app.models.attendance import Attendance
from school_app.enums.attendance import AttendanceStatus
from school_app.models.school_fees import Invoice, Payment
from school_app.enums.school_fees import PaymentStatus
from school_app.modules.grading.services.grade_service import calculate_grade


def _calculate_fees_for_student(invoices):
    """
    Calculate the financial metrics for a student's invoices.

    Returns:
        {
            "total_expected": Decimal,
            "total_paid": Decimal,
            "balance": Decimal,
            "fees_status": str,
        }

    Only CONFIRMED payments are counted.

    Status rules:
        - paid_up:          paid >= expected
        - partially_paid:   0 < paid < expected
        - outstanding:      paid == 0
        - no_fees_on_record: no invoices
    """

    if not invoices:
        return {
            "total_expected": Decimal("0.00"),
            "total_paid": Decimal("0.00"),
            "balance": Decimal("0.00"),
            "fees_status": "no_fees_on_record",
        }

    invoice_ids = [
        invoice.id
        for invoice in invoices
        if invoice.id is not None
    ]

    # ------------------------------------------------------------
    # Total amount expected.
    #
    # Prefer final_amount when it exists, then total_amount.
    # Subtract any waived amount.
    # ------------------------------------------------------------
    total_expected = sum(
        (
            (
                invoice.final_amount
                or invoice.total_amount
                or Decimal("0.00")
            )
            - (
                invoice.waived_amount
                or Decimal("0.00")
            )
        )
        for invoice in invoices
    )

    # Never allow expected amount to become negative.
    total_expected = max(
        total_expected,
        Decimal("0.00"),
    )

    # ------------------------------------------------------------
    # Total confirmed payments.
    #
    # IMPORTANT:
    # Only CONFIRMED payments count.
    # FAILED, PENDING, CANCELLED, etc. do not reduce balance.
    # ------------------------------------------------------------
    total_paid = (
        db.session.scalar(
            select(
                func.coalesce(
                    func.sum(Payment.amount),
                    Decimal("0.00"),
                )
            ).where(
                Payment.invoice_id.in_(invoice_ids),
                Payment.status == PaymentStatus.CONFIRMED,
            )
        )
        or Decimal("0.00")
    )

    total_paid = max(
        total_paid,
        Decimal("0.00"),
    )

    # ------------------------------------------------------------
    # Outstanding balance.
    # ------------------------------------------------------------
    balance = max(
        total_expected - total_paid,
        Decimal("0.00"),
    )

    # ------------------------------------------------------------
    # Fees status.
    #
    # IMPORTANT:
    # A student with some confirmed payment but less than the
    # expected amount is PARTIALLY PAID, not outstanding.
    # ------------------------------------------------------------
    if total_expected <= Decimal("0.00"):
        fees_status = "paid_up"

    elif total_paid >= total_expected:
        fees_status = "paid_up"

    elif total_paid > Decimal("0.00"):
        fees_status = "partially_paid"

    else:
        fees_status = "outstanding"

    return {
        "total_expected": total_expected,
        "total_paid": total_paid,
        "balance": balance,
        "fees_status": fees_status,
    }


# Keep this helper for backwards compatibility with any other code
# that may already import/use it.
def _fees_status_for_student(invoices):
    """
    Backwards-compatible wrapper returning only the fees status.
    """
    return _calculate_fees_for_student(invoices)["fees_status"]


def get_admin_report_students(
    classroom_id=None,
    gender=None,
    session_id=None,
    term_id=None,
    is_active=None,
    start_date=None,
    end_date=None,
    page=1,
    page_size=50,
):
    # ------------------------------------------------------------
    # 1. Filter students
    #
    # IMPORTANT:
    # session_id and term_id are NOT used against
    # Student.current_session_id/current_term_id.
    #
    # The report can be requested for a session/term even when the
    # student's "current" fields are not populated.
    #
    # Session/term filtering is applied to:
    # - exams/results
    # - attendance
    # - invoices
    # ------------------------------------------------------------
    query = select(Student)

    if classroom_id is not None:
        query = query.where(
            Student.classroom_id == classroom_id
        )

    if gender is not None:
        query = query.where(
            Student.gender == gender
        )

    if is_active is not None:
        query = query.where(
            Student.is_active == is_active
        )

    if start_date is not None:
        query = query.where(
            Student.created_at >= start_date
        )

    if end_date is not None:
        query = query.where(
            Student.created_at <= end_date
        )

    students = (
        db.session.execute(query)
        .scalars()
        .all()
    )

    total_students = len(students)

    active_count = sum(
        1
        for student in students
        if student.is_active
    )

    inactive_count = (
        total_students - active_count
    )

    # ------------------------------------------------------------
    # 2. Gender breakdown
    # ------------------------------------------------------------
    by_gender = defaultdict(int)

    for student in students:
        by_gender[
            student.gender or "unspecified"
        ] += 1

    # ------------------------------------------------------------
    # 3. Classroom names / breakdown
    # ------------------------------------------------------------
    classroom_ids = {
        student.classroom_id
        for student in students
        if student.classroom_id is not None
    }

    classroom_names = (
        {
            classroom.id: classroom.name
            for classroom in (
                db.session.execute(
                    select(Classroom).where(
                        Classroom.id.in_(classroom_ids)
                    )
                )
                .scalars()
                .all()
            )
        }
        if classroom_ids
        else {}
    )

    by_classroom = defaultdict(int)

    for student in students:
        by_classroom[
            student.classroom_id
        ] += 1

    by_classroom_report = [
        {
            "classroom_id": classroom_id,
            "classroom_name": (
                classroom_names.get(
                    classroom_id,
                    "Unknown",
                )
                if classroom_id
                else "Unassigned"
            ),
            "count": count,
        }
        for classroom_id, count in by_classroom.items()
    ]

    by_classroom_report.sort(
        key=lambda item: item["classroom_name"]
    )

    # ------------------------------------------------------------
    # 4. Session names / breakdown
    # ------------------------------------------------------------
    session_ids = {
        student.current_session_id
        for student in students
        if student.current_session_id is not None
    }

    session_names = (
        {
            session.id: session.name
            for session in (
                db.session.execute(
                    select(AcademicSession).where(
                        AcademicSession.id.in_(session_ids)
                    )
                )
                .scalars()
                .all()
            )
        }
        if session_ids
        else {}
    )

    by_session = defaultdict(int)

    for student in students:
        by_session[
            student.current_session_id
        ] += 1

    by_session_report = [
        {
            "session_id": sid,
            "session_name": (
                session_names.get(
                    sid,
                    "Unknown",
                )
                if sid
                else "Unassigned"
            ),
            "count": count,
        }
        for sid, count in by_session.items()
    ]

    by_session_report.sort(
        key=lambda item: item["session_name"]
    )

    # ------------------------------------------------------------
    # 5. Term names / breakdown
    # ------------------------------------------------------------
    term_ids = {
        student.current_term_id
        for student in students
        if student.current_term_id is not None
    }

    term_names = (
        {
            term.id: term.name
            for term in (
                db.session.execute(
                    select(Term).where(
                        Term.id.in_(term_ids)
                    )
                )
                .scalars()
                .all()
            )
        }
        if term_ids
        else {}
    )

    by_term = defaultdict(int)

    for student in students:
        by_term[
            student.current_term_id
        ] += 1

    by_term_report = [
        {
            "term_id": tid,
            "term_name": (
                term_names.get(
                    tid,
                    "Unknown",
                )
                if tid
                else "Unassigned"
            ),
            "count": count,
        }
        for tid, count in by_term.items()
    ]

    by_term_report.sort(
        key=lambda item: item["term_name"]
    )

    # ------------------------------------------------------------
    # 6. Sort and paginate students
    # ------------------------------------------------------------
    students_sorted = sorted(
        students,
        key=lambda student: student.full_name or "",
    )

    total_students_matched = len(
        students_sorted
    )

    page = max(
        int(page or 1),
        1,
    )

    page_size = max(
        int(page_size or 50),
        1,
    )

    start = (
        page - 1
    ) * page_size

    page_of_students = students_sorted[
        start:start + page_size
    ]

    # ------------------------------------------------------------
    # 7. Detailed student rows
    # ------------------------------------------------------------
    students_report = []

    for student in page_of_students:

        # ========================================================
        # Academic performance
        # ========================================================
        academic_query = (
            select(Result.marks_obtained)
            .join(
                Exam,
                Result.exam_id == Exam.id,
            )
            .where(
                Result.student_id == student.id
            )
        )

        if session_id is not None:
            academic_query = academic_query.where(
                Exam.session_id == session_id
            )

        if term_id is not None:
            # If Exam has term_id, use it.
            # This is intentionally guarded so that this report
            # does not fail on projects where Exam does not expose
            # term_id.
            if hasattr(Exam, "term_id"):
                academic_query = academic_query.where(
                    Exam.term_id == term_id
                )

        marks = (
            db.session.execute(academic_query)
            .scalars()
            .all()
        )

        marks = [
            mark
            for mark in marks
            if mark is not None
        ]

        average = (
            round(
                sum(marks) / len(marks),
                2,
            )
            if marks
            else None
        )

        grade = (
            calculate_grade(average)
            if average is not None
            else None
        )

        # ========================================================
        # Attendance
        # ========================================================
        attendance_query = (
            select(Attendance.status)
            .where(
                Attendance.student_id == student.id
            )
        )

        if session_id is not None:
            if hasattr(Attendance, "session_id"):
                attendance_query = attendance_query.where(
                    Attendance.session_id == session_id
                )

        if term_id is not None:
            attendance_query = attendance_query.where(
                Attendance.term_id == term_id
            )

        statuses = (
            db.session.execute(
                attendance_query
            )
            .scalars()
            .all()
        )

        attendance_rate = (
            round(
                sum(
                    1
                    for status in statuses
                    if status == AttendanceStatus.PRESENT
                )
                / len(statuses)
                * 100,
                1,
            )
            if statuses
            else None
        )

        # ========================================================
        # Fees / financial metrics
        # ========================================================
        invoice_query = (
            select(Invoice)
            .where(
                Invoice.student_id == student.id
            )
        )

        if session_id is not None:
            invoice_query = invoice_query.where(
                Invoice.session_id == session_id
            )

        if term_id is not None:
            invoice_query = invoice_query.where(
                Invoice.term_id == term_id
            )

        invoices = (
            db.session.execute(invoice_query)
            .scalars()
            .all()
        )

        fees = _calculate_fees_for_student(
            invoices
        )

        # Convert Decimal values to float for JSON/API
        # compatibility and to match test expectations.
        total_expected = float(
            fees["total_expected"]
        )

        total_paid = float(
            fees["total_paid"]
        )

        balance = float(
            fees["balance"]
        )

        fees_status = fees["fees_status"]

        # ========================================================
        # Student status
        #
        # API/test contract:
        #   paid           -> fully paid
        #   partially_paid -> partially paid
        #   unpaid         -> no confirmed payment
        #
        # Keep fees_status as the financial/internal status while
        # exposing the API-compatible `status` expected by tests.
        # ========================================================
        if fees_status == "paid_up":
            status = "paid"

        elif fees_status == "partially_paid":
            status = "partially_paid"

        elif fees_status == "outstanding":
            status = "unpaid"

        else:
            status = fees_status

        # ========================================================
        # Final student row
        # ========================================================
        students_report.append(
            {
                "student_id": student.id,
                "full_name": student.full_name,
                "admission_number": student.admission_number,
                "classroom_id": student.classroom_id,
                "classroom_name": (
                    classroom_names.get(
                        student.classroom_id,
                        "Unknown",
                    )
                    if student.classroom_id
                    else "Unassigned"
                ),
                "gender": student.gender,
                "is_active": student.is_active,

                "current_session_name": (
                    session_names.get(
                        student.current_session_id
                    )
                    if student.current_session_id
                    else None
                ),

                "current_term_name": (
                    term_names.get(
                        student.current_term_id
                    )
                    if student.current_term_id
                    else None
                ),

                "academic_average": average,
                "grade": grade,
                "attendance_rate": attendance_rate,

                "total_expected": total_expected,
                "total_paid": total_paid,
                "balance": balance,
                "fees_status": fees_status,

                "status": status,
            }
        )

    # ------------------------------------------------------------
    # 8. Return report
    # ------------------------------------------------------------
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
            "total_pages": (
                (
                    total_students_matched
                    + page_size
                    - 1
                )
                // page_size
                if total_students_matched
                else 0
            ),
        },
    }
