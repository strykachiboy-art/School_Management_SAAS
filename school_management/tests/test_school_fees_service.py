import pytest
from datetime import date, timedelta
from school_app.extensions import db
from school_app.models.school_fees import FeeStructure, Invoice, Payment
from school_app.models.student import Student
from school_app.enums.school_fees import FeeCategory, InvoiceStatus, PaymentStatus
from school_app.modules.school_fees.requests.school_fees_request import (
    CreateFeeStructureRequest,
    UpdateFeeStructureRequest,
    GenerateInvoicesRequest,
    RecordPaymentRequest,
)
from school_app.modules.school_fees.services.school_fees_service import (
    create_fee_structure,
    update_fee_structure,
    generate_invoices_for_term,
    record_payment,
    mark_overdue_invoices,
)

def test_create_fee_structure(app, db_session, admin_actor_id, classroom, academic_session, term, school):
    payload = CreateFeeStructureRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        category=FeeCategory.TUITION,
        amount=50000.0
    )
    structure = create_fee_structure(school.id, payload, actor_id=admin_actor_id)

    assert structure is not None
    assert structure.amount == 50000.0
    assert structure.category == FeeCategory.TUITION

def test_generate_invoices_for_term(app, db_session, admin_actor_id, classroom, academic_session, term, student, school):
    student.classroom_id = classroom.id
    db.session.merge(student)
    db.session.commit()

    payload_struct = CreateFeeStructureRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        category=FeeCategory.TUITION,
        amount=50000.0
    )
    create_fee_structure(school.id, payload_struct, actor_id=admin_actor_id)

    payload = GenerateInvoicesRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        due_date=date.today() + timedelta(days=30)
    )

    invoices = generate_invoices_for_term(school.id, payload, actor_id=admin_actor_id)

    assert len(invoices) >= 1
    assert invoices[0].total_amount == 50000.0
    assert invoices[0].status == InvoiceStatus.UNPAID

def test_record_payment_success(app, db_session, admin_actor_id, classroom, academic_session, term, student, school):
    student.classroom_id = classroom.id
    db.session.merge(student)
    db.session.commit()

    payload_struct = CreateFeeStructureRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        category=FeeCategory.TUITION,
        amount=50000.0
    )
    create_fee_structure(school.id, payload_struct, actor_id=admin_actor_id)

    payload_gen = GenerateInvoicesRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        due_date=date.today() + timedelta(days=30)
    )
    invoices = generate_invoices_for_term(school.id, payload_gen, actor_id=admin_actor_id)
    invoice = invoices[0]

    payload = RecordPaymentRequest(
        invoice_id=invoice.id,
        amount=invoice.total_amount,
        payment_method="bank_transfer"
    )

    payment = record_payment(school.id, payload, recorded_by=admin_actor_id)

    refreshed_invoice = db.session.get(Invoice, invoice.id)

    assert payment is not None
    assert payment.amount == invoice.total_amount
    assert refreshed_invoice.amount_paid == invoice.total_amount
    assert refreshed_invoice.status == InvoiceStatus.PAID

def test_mark_overdue_invoices(app, db_session, admin_actor_id, classroom, academic_session, term, student, school):
    student.classroom_id = classroom.id
    db.session.merge(student)
    db.session.commit()

    payload_struct = CreateFeeStructureRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        category=FeeCategory.TUITION,
        amount=50000.0
    )
    create_fee_structure(school.id, payload_struct, actor_id=admin_actor_id)

    payload_gen = GenerateInvoicesRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        due_date=date.today() + timedelta(days=30)
    )
    invoices = generate_invoices_for_term(school.id, payload_gen, actor_id=admin_actor_id)
    invoice = invoices[0]

    invoice.due_date = date.today() - timedelta(days=5)
    db.session.commit()

    count = mark_overdue_invoices(school.id, as_of=date.today())

    refreshed_invoice = db.session.get(Invoice, invoice.id)

    assert count >= 1
    assert refreshed_invoice.status == InvoiceStatus.OVERDUE