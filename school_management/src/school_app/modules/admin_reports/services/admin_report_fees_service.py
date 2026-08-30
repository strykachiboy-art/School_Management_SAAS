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


def _filtered_invoices_query(session_id=None, term_id=None, classroom_id=None,
                              student_id=None, start_date=None, end_date=None):
    query = select(Invoice)
    needs_student_join = classroom_id is not None
    if needs_student_join:
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


def get_admin_report_fees(session_id=None, term_id=None, classroom_id=None,
                           student_id=None, start_date=None, end_date=None):
    invoices = db.session.execute(
        _filtered_invoices_query(session_id, term_id, classroom_id, student_id, start_date, end_date)
    ).scalars().all()

    if not invoices:
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

    total_expected = sum((inv.final_amount for inv in invoices), Decimal("0.00"))
    total_paid = sum((inv.amount_paid for inv in invoices), Decimal("0.00"))
    total_outstanding = sum((inv.balance for inv in invoices), Decimal("0.00"))

    invoice_ids = [inv.id for inv in invoices]
    payment_count = db.session.scalar(
        select(func.count()).select_from(Payment)
        .where(Payment.invoice_id.in_(invoice_ids), Payment.status == PaymentStatus.CONFIRMED)
    )

    payment_method_rows = db.session.execute(
        select(Payment.payment_method, func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(Payment.invoice_id.in_(invoice_ids), Payment.status == PaymentStatus.CONFIRMED)
        .group_by(Payment.payment_method)
    ).all()
    collection_by_payment_method = {method.value: float(total) for method, total in payment_method_rows}

    # ---- Gateway payments stuck outside CONFIRMED ----
    # Confirmed money already flows through amount_paid above; this
    # surfaces checkouts that were started but never landed, so an
    # admin isn't blind to money that's pending or failed at the gateway.
    pending_gateway_row = db.session.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(
            Payment.invoice_id.in_(invoice_ids),
            Payment.status == PaymentStatus.PENDING,
            Payment.gateway.is_not(None),
        )
    ).one()
    failed_gateway_row = db.session.execute(
        select(func.count(), func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(
            Payment.invoice_id.in_(invoice_ids),
            Payment.status == PaymentStatus.FAILED,
            Payment.gateway.is_not(None),
        )
    ).one()
    pending_gateway_payments = {"count": pending_gateway_row[0], "total_amount": float(pending_gateway_row[1])}
    failed_gateway_payments = {"count": failed_gateway_row[0], "total_amount": float(failed_gateway_row[1])}

    # ---- Collection by classroom / session / term ----
    # These break the *matched* invoice set down by dimension, so if
    # you've already filtered to one classroom, "by_classroom" will
    # trivially show one row — the value is in calling this with a
    # broader filter (e.g. just session_id) and seeing collection
    # split across every classroom in that session at once, rather
    # than having to call the endpoint once per classroom.
    student_ids = {inv.student_id for inv in invoices}
    student_classroom = {
        s.id: s.classroom_id for s in db.session.execute(
            select(Student).where(Student.id.in_(student_ids))
        ).scalars().all()
    } if student_ids else {}

    classroom_ids_present = {cid for cid in student_classroom.values() if cid is not None}
    classroom_names = {
        c.id: c.name for c in db.session.execute(
            select(Classroom).where(Classroom.id.in_(classroom_ids_present))
        ).scalars().all()
    } if classroom_ids_present else {}

    session_ids_present = {inv.session_id for inv in invoices}
    session_names = {
        s.id: s.name for s in db.session.execute(
            select(AcademicSession).where(AcademicSession.id.in_(session_ids_present))
        ).scalars().all()
    } if session_ids_present else {}

    term_ids_present = {inv.term_id for inv in invoices}
    term_names = {
        t.id: t.name for t in db.session.execute(
            select(Term).where(Term.id.in_(term_ids_present))
        ).scalars().all()
    } if term_ids_present else {}

    by_classroom_totals = defaultdict(lambda: {"expected": Decimal("0.00"), "paid": Decimal("0.00")})
    by_session_totals = defaultdict(lambda: {"expected": Decimal("0.00"), "paid": Decimal("0.00")})
    by_term_totals = defaultdict(lambda: {"expected": Decimal("0.00"), "paid": Decimal("0.00")})

    for inv in invoices:
        cid = student_classroom.get(inv.student_id)
        by_classroom_totals[cid]["expected"] += inv.final_amount
        by_classroom_totals[cid]["paid"] += inv.amount_paid
        by_session_totals[inv.session_id]["expected"] += inv.final_amount
        by_session_totals[inv.session_id]["paid"] += inv.amount_paid
        by_term_totals[inv.term_id]["expected"] += inv.final_amount
        by_term_totals[inv.term_id]["paid"] += inv.amount_paid

    collection_by_classroom = sorted([
        {
            "classroom_id": cid,
            "classroom_name": classroom_names.get(cid, "Unknown") if cid else "Unassigned",
            "total_expected": float(totals["expected"]),
            "total_paid": float(totals["paid"]),
        }
        for cid, totals in by_classroom_totals.items()
    ], key=lambda c: c["classroom_name"])

    collection_by_session = sorted([
        {
            "session_id": sid,
            "session_name": session_names.get(sid, "Unknown"),
            "total_expected": float(totals["expected"]),
            "total_paid": float(totals["paid"]),
        }
        for sid, totals in by_session_totals.items()
    ], key=lambda s: s["session_name"])

    collection_by_term = sorted([
        {
            "term_id": tid,
            "term_name": term_names.get(tid, "Unknown"),
            "total_expected": float(totals["expected"]),
            "total_paid": float(totals["paid"]),
        }
        for tid, totals in by_term_totals.items()
    ], key=lambda t: t["term_name"])

    # ---- Per-student aggregation for fully/partially/unpaid buckets ----
    by_student = defaultdict(list)
    for inv in invoices:
        by_student[inv.student_id].append(inv)

    fully_paid = partially_paid = unpaid = 0
    for student_id_key, student_invoices in by_student.items():
        owed = sum((inv.final_amount - inv.waived_amount for inv in student_invoices), Decimal("0.00"))
        paid = sum((inv.amount_paid for inv in student_invoices), Decimal("0.00"))
        if owed <= 0 or paid >= owed:
            fully_paid += 1
        elif paid > 0:
            partially_paid += 1
        else:
            unpaid += 1

    collection_rate = (
        round(float(total_paid) / float(total_expected) * 100, 1)
        if total_expected else None
    )

    return {
        "total_expected": float(total_expected),
        "total_paid": float(total_paid),
        "total_outstanding": float(total_outstanding),
        "payment_count": payment_count,
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