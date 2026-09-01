# src/school_app/modules/admin_reports/services/admin_report_fees_service.py

from decimal import Decimal
from collections import defaultdict

from sqlalchemy import select, func

from school_app.extensions import db
from school_app.models.school_fees import Invoice, Payment
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.models.academic_session import AcademicSession
from school_app.models.term import Term
from school_app.enums.school_fees import PaymentStatus


def _filtered_invoices_query(
    session_id=None,
    term_id=None,
    classroom_id=None,
    student_id=None,
    start_date=None,
    end_date=None,
):
    query = select(Invoice)

    if classroom_id is not None:
        query = query.join(Student, Invoice.student_id == Student.id)

    if session_id is not None:
        query = query.where(Invoice.session_id == session_id)

    if term_id is not None:
        query = query.where(Invoice.term_id == term_id)

    if classroom_id is not None:
        query = query.where(Student.classroom_id == classroom_id)

    if student_id is not None:
        query = query.where(Invoice.student_id == student_id)

    if start_date is not None:
        query = query.where(Invoice.created_at >= start_date)

    if end_date is not None:
        query = query.where(Invoice.created_at <= end_date)

    return query


def _empty_report():
    return {
        "total_expected": 0.0,
        "total_paid": 0.0,
        "total_outstanding": 0.0,
        "payment_count": 0,
        "fully_paid_students": 0,
        "partially_paid_students": 0,
        "unpaid_students": 0,
        "collection_rate": None,
        "collection_by_payment_method": {},
        "pending_gateway_payments": {"count": 0, "total_amount": 0.0},
        "failed_gateway_payments": {"count": 0, "total_amount": 0.0},
        "collection_by_classroom": [],
        "collection_by_session": [],
        "collection_by_term": [],
    }


def get_admin_report_fees(
    session_id=None,
    term_id=None,
    classroom_id=None,
    student_id=None,
    start_date=None,
    end_date=None,
):
    # ------------------------------------------------------------------
    # 1. Get invoices matching the requested filters
    # ------------------------------------------------------------------
    invoices = (
        db.session.execute(
            _filtered_invoices_query(
                session_id=session_id,
                term_id=term_id,
                classroom_id=classroom_id,
                student_id=student_id,
                start_date=start_date,
                end_date=end_date,
            )
        )
        .scalars()
        .all()
    )

    if not invoices:
        return _empty_report()

    invoice_ids = [invoice.id for invoice in invoices]

    # ------------------------------------------------------------------
    # 2. Calculate expected amount directly from invoices
    # ------------------------------------------------------------------
    total_expected = sum((invoice.final_amount or Decimal("0.00") for invoice in invoices), Decimal("0.00"))

    # ------------------------------------------------------------------
    # 3. Aggregate CONFIRMED payments directly from Payment
    # ------------------------------------------------------------------
    confirmed_payment_rows = db.session.execute(
        select(Payment.invoice_id, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.invoice_id.in_(invoice_ids), Payment.status == PaymentStatus.CONFIRMED)
        .group_by(Payment.invoice_id)
    ).all()

    confirmed_paid_by_invoice = {
        invoice_id: Decimal(str(total or 0)) for invoice_id, total in confirmed_payment_rows
    }

    # Ensure every invoice has an entry
    for invoice_id in invoice_ids:
        confirmed_paid_by_invoice.setdefault(invoice_id, Decimal("0.00"))

    # ------------------------------------------------------------------
    # 4. Calculate total paid and outstanding
    # ------------------------------------------------------------------
    total_paid = sum(confirmed_paid_by_invoice[invoice_id] for invoice_id in invoice_ids)

    total_outstanding = Decimal("0.00")
    for invoice in invoices:
        expected = invoice.final_amount or Decimal("0.00")
        waived = getattr(invoice, "waived_amount", Decimal("0.00")) or Decimal("0.00")
        paid = confirmed_paid_by_invoice[invoice.id]
        outstanding = expected - waived - paid
        if outstanding < 0:
            outstanding = Decimal("0.00")
        total_outstanding += outstanding

    # ------------------------------------------------------------------
    # 5. Confirmed payment count
    # ------------------------------------------------------------------
    payment_count = (
        db.session.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.invoice_id.in_(invoice_ids), Payment.status == PaymentStatus.CONFIRMED)
        )
        or 0
    )

    # ------------------------------------------------------------------
    # 6. Collection by payment method
    # ------------------------------------------------------------------
    payment_method_rows = db.session.execute(
        select(Payment.payment_method, func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.invoice_id.in_(invoice_ids), Payment.status == PaymentStatus.CONFIRMED)
        .group_by(Payment.payment_method)
    ).all()

    collection_by_payment_method = {}
    for method, total in payment_method_rows:
        if method is None:
            key = "UNKNOWN"
        elif hasattr(method, "value"):
            key = method.value
        else:
            key = str(method)
        collection_by_payment_method[key] = float(total or Decimal("0.00"))

    # ------------------------------------------------------------------
    # 7. Pending gateway payments
    # ------------------------------------------------------------------
    pending_gateway_row = db.session.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.invoice_id.in_(invoice_ids),
            Payment.status == PaymentStatus.PENDING,
            Payment.gateway.is_not(None),
        )
    ).one()

    pending_gateway_payments = {
        "count": int(pending_gateway_row[0] or 0),
        "total_amount": float(pending_gateway_row[1] or Decimal("0.00")),
    }

    # ------------------------------------------------------------------
    # 8. Failed gateway payments
    # ------------------------------------------------------------------
    failed_gateway_row = db.session.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.invoice_id.in_(invoice_ids),
            Payment.status == PaymentStatus.FAILED,
            Payment.gateway.is_not(None),
        )
    ).one()

    failed_gateway_payments = {
        "count": int(failed_gateway_row[0] or 0),
        "total_amount": float(failed_gateway_row[1] or Decimal("0.00")),
    }

    # ------------------------------------------------------------------
    # 9. Load students and classrooms
    # ------------------------------------------------------------------
    student_ids = {invoice.student_id for invoice in invoices if invoice.student_id is not None}

    students = (
        db.session.execute(select(Student).where(Student.id.in_(student_ids))).scalars().all()
        if student_ids
        else []
    )

    student_classroom = {student.id: student.classroom_id for student in students}

    classroom_ids = {cid for cid in student_classroom.values() if cid is not None}

    classrooms = (
        db.session.execute(select(Classroom).where(Classroom.id.in_(classroom_ids))).scalars().all()
        if classroom_ids
        else []
    )

    classroom_names = {classroom.id: classroom.name for classroom in classrooms}

    # ------------------------------------------------------------------
    # 10. Load sessions
    # ------------------------------------------------------------------
    session_ids = {invoice.session_id for invoice in invoices if invoice.session_id is not None}

    sessions = (
        db.session.execute(select(AcademicSession).where(AcademicSession.id.in_(session_ids))).scalars().all()
        if session_ids
        else []
    )

    session_names = {academic_session.id: academic_session.name for academic_session in sessions}

    # ------------------------------------------------------------------
    # 11. Load terms
    # ------------------------------------------------------------------
    term_ids = {invoice.term_id for invoice in invoices if invoice.term_id is not None}

    terms = (
        db.session.execute(select(Term).where(Term.id.in_(term_ids))).scalars().all() if term_ids else []
    )

    term_names = {term.id: term.name for term in terms}

    # ------------------------------------------------------------------
    # 12. Collection breakdowns
    # ------------------------------------------------------------------
    by_classroom_totals = defaultdict(lambda: {"expected": Decimal("0.00"), "paid": Decimal("0.00")})
    by_session_totals = defaultdict(lambda: {"expected": Decimal("0.00"), "paid": Decimal("0.00")})
    by_term_totals = defaultdict(lambda: {"expected": Decimal("0.00"), "paid": Decimal("0.00")})

    for invoice in invoices:
        expected = invoice.final_amount or Decimal("0.00")
        paid = confirmed_paid_by_invoice[invoice.id]

        classroom_id_value = student_classroom.get(invoice.student_id)

        by_classroom_totals[classroom_id_value]["expected"] += expected
        by_classroom_totals[classroom_id_value]["paid"] += paid

        by_session_totals[invoice.session_id]["expected"] += expected
        by_session_totals[invoice.session_id]["paid"] += paid

        by_term_totals[invoice.term_id]["expected"] += expected
        by_term_totals[invoice.term_id]["paid"] += paid

    collection_by_classroom = sorted(
        [
            {
                "classroom_id": classroom_id_value,
                "classroom_name": (
                    classroom_names.get(classroom_id_value, "Unknown")
                    if classroom_id_value is not None
                    else "Unassigned"
                ),
                "total_expected": float(totals["expected"]),
                "total_paid": float(totals["paid"]),
            }
            for classroom_id_value, totals in by_classroom_totals.items()
        ],
        key=lambda item: item["classroom_name"],
    )

    collection_by_session = sorted(
        [
            {
                "session_id": session_id_value,
                "session_name": session_names.get(session_id_value, "Unknown"),
                "total_expected": float(totals["expected"]),
                "total_paid": float(totals["paid"]),
            }
            for session_id_value, totals in by_session_totals.items()
        ],
        key=lambda item: item["session_name"],
    )

    collection_by_term = sorted(
        [
            {
                "term_id": term_id_value,
                "term_name": term_names.get(term_id_value, "Unknown"),
                "total_expected": float(totals["expected"]),
                "total_paid": float(totals["paid"]),
            }
            for term_id_value, totals in by_term_totals.items()
        ],
        key=lambda item: item["term_name"],
    )

    # ------------------------------------------------------------------
    # 13. Student payment-status buckets
    # ------------------------------------------------------------------
    by_student = defaultdict(list)
    for invoice in invoices:
        by_student[invoice.student_id].append(invoice)

    fully_paid = 0
    partially_paid = 0
    unpaid = 0

    for student_id_value, student_invoices in by_student.items():
        owed = Decimal("0.00")
        paid = Decimal("0.00")

        for invoice in student_invoices:
            expected = invoice.final_amount or Decimal("0.00")
            waived = getattr(invoice, "waived_amount", Decimal("0.00")) or Decimal("0.00")
            owed += max(expected - waived, Decimal("0.00"))
            paid += confirmed_paid_by_invoice[invoice.id]

        if owed <= 0 or paid >= owed:
            fully_paid += 1
        elif paid > 0:
            partially_paid += 1
        else:
            unpaid += 1

    # ------------------------------------------------------------------
    # 14. Collection rate
    # ------------------------------------------------------------------
    collection_rate = round(float(total_paid) / float(total_expected) * 100, 1) if total_expected else None

    # ------------------------------------------------------------------
    # 15. Final report
    # ------------------------------------------------------------------
    return {
        "total_expected": float(total_expected),
        "total_paid": float(total_paid),
        "total_outstanding": float(total_outstanding),
        "payment_count": int(payment_count),
        "fully_paid_students": fully_paid,
        "partially_paid_students": partially_paid,
        "unpaid_students": unpaid,
        "collection_rate": collection_rate,
        "collection_by_payment_method": collection_by_payment_method,
        "pending_gateway_payments": pending_gateway_payments,
        "failed_gateway_payments": failed_gateway_payments,
        "collection_by_classroom": collection_by_classroom,
        "collection_by_session": collection_by_session,
        "collection_by_term": collection_by_term,
    }
