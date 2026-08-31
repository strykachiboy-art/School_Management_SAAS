import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from school_app.extensions import db
from school_app.models.school_fees import Invoice, Payment
from school_app.enums.school_fees import (
    FeeCategory, InvoiceStatus, PaymentStatus, PaymentGateway,
)
from school_app.modules.school_fees.requests.school_fees_request import (
    CreateFeeStructureRequest,
    GenerateInvoicesRequest,
    InitiateGatewayPaymentRequest,
)
from school_app.modules.school_fees.services.school_fees_service import (
    create_fee_structure,
    generate_invoices_for_term,
    initiate_gateway_payment,
    confirm_gateway_payment,
)


def _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school, amount=50000.0):
    """Shared setup: fee structure -> invoice, same pattern as
    test_school_fees_service.py's test_record_payment_success."""
    student.classroom_id = classroom.id
    db.session.merge(student)
    db.session.commit()

    payload_struct = CreateFeeStructureRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        category=FeeCategory.TUITION,
        amount=amount,
    )
    create_fee_structure(school.id, payload_struct, actor_id=admin_actor_id)

    payload_gen = GenerateInvoicesRequest(
        classroom_id=classroom.id,
        session_id=academic_session.id,
        term_id=term.id,
        due_date=date.today() + timedelta(days=30),
    )
    invoices = generate_invoices_for_term(school.id, payload_gen, actor_id=admin_actor_id)
    return invoices[0]


def _gateway_payload(invoice, amount=None):
    return InitiateGatewayPaymentRequest(
        invoice_id=invoice.id,
        amount=amount if amount is not None else invoice.total_amount,
        gateway=PaymentGateway.PAYSTACK,
        currency="NGN",
        email="parent@example.com",
        callback_url="https://example.com/fees/callback",
    )


def test_initiate_gateway_payment_creates_pending_payment(
    app, db_session, admin_actor_id, classroom, academic_session, term, student, school
):
    invoice = _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school)

    mock_gateway = MagicMock()
    mock_gateway.initialize.return_value = MagicMock(
        checkout_url="https://paystack.com/checkout/abc123",
        gateway_reference="ps_ref_abc123",
        raw_response={"status": True},
    )

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=mock_gateway) as mock_get_gateway:
        result = initiate_gateway_payment(school.id, _gateway_payload(invoice))

    mock_get_gateway.assert_called_once_with(PaymentGateway.PAYSTACK)
    mock_gateway.initialize.assert_called_once()

    payment = result["payment"]
    refreshed_invoice = db.session.get(Invoice, invoice.id)

    assert result["checkout_url"] == "https://paystack.com/checkout/abc123"
    assert payment.status == PaymentStatus.PENDING
    assert payment.gateway == PaymentGateway.PAYSTACK
    assert payment.gateway_reference == "ps_ref_abc123"
    assert payment.recorded_by is None
    assert refreshed_invoice.amount_paid == 0
    assert refreshed_invoice.status == InvoiceStatus.UNPAID


def test_initiate_gateway_payment_exceeds_balance(
    app, db_session, admin_actor_id, classroom, academic_session, term, student, school
):
    invoice = _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway"):
        with pytest.raises(ValueError):
            initiate_gateway_payment(school.id, _gateway_payload(invoice, amount=invoice.total_amount + 1))


def test_initiate_gateway_payment_marks_failed_on_gateway_error(
    app, db_session, admin_actor_id, classroom, academic_session, term, student, school
):
    invoice = _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school)

    mock_gateway = MagicMock()
    mock_gateway.initialize.side_effect = RuntimeError("Paystack initialize failed: bad request")

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=mock_gateway):
        with pytest.raises(ValueError):
            initiate_gateway_payment(school.id, _gateway_payload(invoice))

    payment = Payment.query.filter_by(invoice_id=invoice.id).first()
    assert payment.status == PaymentStatus.FAILED


def test_confirm_gateway_payment_applies_to_invoice(
    app, db_session, admin_actor_id, classroom, academic_session, term, student, school
):
    invoice = _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school)

    init_gateway = MagicMock()
    init_gateway.initialize.return_value = MagicMock(
        checkout_url="https://paystack.com/checkout/abc123",
        gateway_reference="ps_ref_abc123",
        raw_response={"status": True},
    )
    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=init_gateway):
        result = initiate_gateway_payment(school.id, _gateway_payload(invoice))

    reference = result["reference"]

    verify_gateway = MagicMock()
    verify_gateway.verify.return_value = MagicMock(
        success=True,
        gateway_reference="ps_ref_abc123",
        amount=invoice.total_amount,
        currency="NGN",
        paid_at="2026-08-26T10:00:00",
        raw_response={"status": True, "data": {"status": "success"}},
    )
    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=verify_gateway):
        confirmed = confirm_gateway_payment(school.id, reference)

    refreshed_invoice = db.session.get(Invoice, invoice.id)

    assert confirmed.status == PaymentStatus.CONFIRMED
    assert confirmed.paid_at is not None
    assert refreshed_invoice.amount_paid == invoice.total_amount
    assert refreshed_invoice.status == InvoiceStatus.PAID


def test_confirm_gateway_payment_is_idempotent(
    app, db_session, admin_actor_id, classroom, academic_session, term, student, school
):
    """A webhook firing twice must not double-apply amount_paid."""
    invoice = _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school)

    init_gateway = MagicMock()
    init_gateway.initialize.return_value = MagicMock(
        checkout_url="https://paystack.com/checkout/abc123",
        gateway_reference="ps_ref_abc123",
        raw_response={"status": True},
    )
    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=init_gateway):
        result = initiate_gateway_payment(school.id, _gateway_payload(invoice))

    reference = result["reference"]

    verify_gateway = MagicMock()
    verify_gateway.verify.return_value = MagicMock(
        success=True,
        gateway_reference="ps_ref_abc123",
        amount=invoice.total_amount,
        currency="NGN",
        paid_at="2026-08-26T10:00:00",
        raw_response={},
    )
    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=verify_gateway):
        confirm_gateway_payment(school.id, reference)
        confirm_gateway_payment(school.id, reference)  # webhook fires again

    refreshed_invoice = db.session.get(Invoice, invoice.id)
    assert refreshed_invoice.amount_paid == invoice.total_amount  # not doubled
    assert verify_gateway.verify.call_count == 1  # second call short-circuits before re-verifying


def test_confirm_gateway_payment_marks_failed_when_gateway_rejects(
    app, db_session, admin_actor_id, classroom, academic_session, term, student, school
):
    invoice = _make_invoice(db_session, admin_actor_id, classroom, academic_session, term, student, school)

    init_gateway = MagicMock()
    init_gateway.initialize.return_value = MagicMock(
        checkout_url="https://paystack.com/checkout/abc123",
        gateway_reference="ps_ref_abc123",
        raw_response={"status": True},
    )
    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=init_gateway):
        result = initiate_gateway_payment(school.id, _gateway_payload(invoice))

    reference = result["reference"]

    verify_gateway = MagicMock()
    verify_gateway.verify.return_value = MagicMock(
        success=False,
        gateway_reference="ps_ref_abc123",
        amount=invoice.total_amount,
        currency="NGN",
        paid_at=None,
        raw_response={"data": {"status": "failed"}},
    )
    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=verify_gateway):
        with pytest.raises(ValueError):
            confirm_gateway_payment(school.id, reference)

    payment = Payment.query.filter_by(reference=reference).first()
    refreshed_invoice = db.session.get(Invoice, invoice.id)

    assert payment.status == PaymentStatus.FAILED
    assert refreshed_invoice.amount_paid == 0
    assert refreshed_invoice.status == InvoiceStatus.UNPAID


def test_confirm_gateway_payment_reference_not_found(app, db_session, school):
    with pytest.raises(Exception):
        confirm_gateway_payment(school.id, "SCH-9999-000000")