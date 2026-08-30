from datetime import date, timedelta
from unittest.mock import patch, MagicMock
import stripe

from school_app.extensions import db
from school_app.models.school_fees import Invoice, Payment
from school_app.enums.school_fees import FeeCategory
from school_app.modules.school_fees.requests.school_fees_request import (
    CreateFeeStructureRequest,
    GenerateInvoicesRequest,
)
from school_app.modules.school_fees.services.school_fees_service import create_fee_structure, generate_invoices_for_term


def _make_invoice(admin_actor_id, classroom, academic_session, term, student, amount=50000.0):
    student.classroom_id = classroom.id
    db.session.merge(student)
    db.session.commit()

    create_fee_structure(
        CreateFeeStructureRequest(
            classroom_id=classroom.id,
            session_id=academic_session.id,
            term_id=term.id,
            category=FeeCategory.TUITION,
            amount=amount,
        ),
        actor_id=admin_actor_id,
    )

    invoices = generate_invoices_for_term(
        GenerateInvoicesRequest(
            classroom_id=classroom.id,
            session_id=academic_session.id,
            term_id=term.id,
            due_date=date.today() + timedelta(days=30),
        ),
        actor_id=admin_actor_id,
    )
    return invoices[0]


def _initiate_payload(invoice, amount=None, gateway="paystack", currency="NGN"):
    return {
        "invoice_id": invoice.id,
        "amount": amount if amount is not None else float(invoice.total_amount),
        "gateway": gateway,
        "currency": currency,
        "email": "parent@example.com",
        "callback_url": "https://example.com/fees/callback",
    }


def _mock_paystack_gateway():
    gw = MagicMock()
    gw.initialize.return_value = MagicMock(
        checkout_url="https://paystack.com/checkout/abc123",
        gateway_reference="ps_ref_abc123",
        raw_response={"status": True},
    )
    return gw


def _mock_stripe_gateway():
    gw = MagicMock()
    gw.initialize.return_value = MagicMock(
        checkout_url="https://checkout.stripe.com/c/pay/cs_test_abc123",
        gateway_reference="cs_test_abc123",
        raw_response={},
    )
    return gw


# ====================================== Payment Initiation Tests ===============================================

def test_initiate_gateway_payment_route_paystack_as_admin(
    client, admin_headers, admin_actor_id, classroom, academic_session, term, student
):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=_mock_paystack_gateway()):
        response = client.post(
            "/fees/payments/gateway/initiate",
            json=_initiate_payload(invoice, gateway="paystack"),
            headers=admin_headers,
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["checkout_url"] == "https://paystack.com/checkout/abc123"
    assert data["payment"]["status"] == "pending"
    assert data["payment"]["gateway"] == "paystack"


def test_initiate_gateway_payment_route_stripe_as_admin(
    client, admin_headers, admin_actor_id, classroom, academic_session, term, student
):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=_mock_stripe_gateway()):
        response = client.post(
            "/fees/payments/gateway/initiate",
            json=_initiate_payload(invoice, gateway="stripe", currency="USD"),
            headers=admin_headers,
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["checkout_url"] == "https://checkout.stripe.com/c/pay/cs_test_abc123"
    assert data["payment"]["status"] == "pending"
    assert data["payment"]["gateway"] == "stripe"


def test_initiate_gateway_payment_route_as_own_student(
    client, student_headers, student, admin_actor_id, classroom, academic_session, term
):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=_mock_paystack_gateway()):
        response = client.post(
            "/fees/payments/gateway/initiate",
            json=_initiate_payload(invoice),
            headers=student_headers,
        )

    assert response.status_code == 201


def test_initiate_gateway_payment_route_as_other_students_invoice_forbidden(
    client, student2_headers, student, admin_actor_id, classroom, academic_session, term
):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    response = client.post(
        "/fees/payments/gateway/initiate",
        json=_initiate_payload(invoice),
        headers=student2_headers,
    )

    assert response.status_code == 403


def test_initiate_gateway_payment_route_invalid_invoice(client, admin_headers):
    response = client.post(
        "/fees/payments/gateway/initiate",
        json={
            "invoice_id": 999999,
            "amount": 5000.0,
            "gateway": "paystack",
            "currency": "NGN",
            "email": "parent@example.com",
            "callback_url": "https://example.com/fees/callback",
        },
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_initiate_gateway_payment_route_missing_fields(client, admin_headers):
    response = client.post(
        "/fees/payments/gateway/initiate",
        json={"invoice_id": 1},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_initiate_gateway_payment_route_requires_auth(client, classroom, academic_session, term, student, admin_actor_id):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    response = client.post("/fees/payments/gateway/initiate", json=_initiate_payload(invoice))
    assert response.status_code == 401


# ====================================== Paystack Webhook Tests ===============================================

def test_gateway_webhook_route_confirms_payment(
    client, admin_headers, admin_actor_id, classroom, academic_session, term, student
):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=_mock_paystack_gateway()):
        init_response = client.post(
            "/fees/payments/gateway/initiate",
            json=_initiate_payload(invoice),
            headers=admin_headers,
        )
    reference = init_response.get_json()["reference"]

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
        response = client.post(
            "/fees/payments/gateway/webhook",
            json={"data": {"reference": reference}},
        )

    assert response.status_code == 200
    assert response.get_json()["received"] is True

    refreshed_invoice = db.session.get(Invoice, invoice.id)
    assert refreshed_invoice.amount_paid == invoice.total_amount


def test_gateway_webhook_route_missing_reference(client):
    response = client.post("/fees/payments/gateway/webhook", json={"data": {}})
    assert response.status_code == 400


def test_gateway_webhook_route_unknown_reference(client):
    response = client.post(
        "/fees/payments/gateway/webhook",
        json={"data": {"reference": "SCH-9999-000000"}},
    )
    assert response.status_code in (400, 404)


# ====================================== Stripe Webhook Tests ===============================================

def test_stripe_webhook_route_confirms_payment(
    client, app, admin_headers, admin_actor_id, classroom, academic_session, term, student
):
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=_mock_stripe_gateway()):
        init_response = client.post(
            "/fees/payments/gateway/initiate",
            json=_initiate_payload(invoice, gateway="stripe", currency="USD"),
            headers=admin_headers,
        )
    reference = init_response.get_json()["reference"]

    mock_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc123",
                "metadata": {"reference": reference},
            }
        },
    }

    verify_gateway = MagicMock()
    verify_gateway.verify.return_value = MagicMock(
        success=True,
        gateway_reference="cs_test_abc123",
        amount=invoice.total_amount,
        currency="USD",
        paid_at="2026-08-26T10:00:00",
        raw_response={},
    )

    with patch("stripe.Webhook.construct_event", return_value=mock_event), \
         patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=verify_gateway):
        response = client.post(
            "/fees/payments/gateway/stripe/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "t=123,v1=signature"},
            content_type="application/json",
        )

    assert response.status_code == 200
    assert response.get_json()["received"] is True

    refreshed_invoice = db.session.get(Invoice, invoice.id)
    assert refreshed_invoice.amount_paid == invoice.total_amount


def test_stripe_webhook_route_missing_secret(client, app):
    app.config["STRIPE_WEBHOOK_SECRET"] = None
    response = client.post(
        "/fees/payments/gateway/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )
    assert response.status_code == 500


def test_stripe_webhook_route_missing_signature(client, app):
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"
    response = client.post("/fees/payments/gateway/stripe/webhook", data=b"{}")
    assert response.status_code == 400


def test_stripe_webhook_route_invalid_signature(client, app):
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"

    with patch("stripe.Webhook.construct_event", side_effect=stripe.error.SignatureVerificationError("Invalid sig", "sig")):
        response = client.post(
            "/fees/payments/gateway/stripe/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "bad_sig"},
        )
    assert response.status_code == 400


def test_stripe_webhook_route_ignored_event_type(client, app):
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"

    mock_event = {"type": "payment_intent.created", "data": {"object": {}}}

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        response = client.post(
            "/fees/payments/gateway/stripe/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "sig"},
        )
    assert response.status_code == 200
    data = response.get_json()
    assert data["received"] is True
    assert data["ignored"] == "payment_intent.created"


def test_stripe_webhook_route_missing_reference_in_metadata(client, app):
    app.config["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"

    mock_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_abc123", "metadata": {}}},
    }

    with patch("stripe.Webhook.construct_event", return_value=mock_event):
        response = client.post(
            "/fees/payments/gateway/stripe/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "sig"},
        )
    assert response.status_code == 400


# ====================================== Direct Verification Tests ===============================================

def test_verify_gateway_payment_route_as_admin(
    client, admin_headers, admin_actor_id, classroom, academic_session, term, student
):
    invoice = _make_invoice(admin_actor_id, classroom, academic_session, term, student)

    with patch("school_app.modules.school_fees.services.school_fees_service.get_gateway", return_value=_mock_paystack_gateway()):
        init_response = client.post(
            "/fees/payments/gateway/initiate",
            json=_initiate_payload(invoice),
            headers=admin_headers,
        )
    reference = init_response.get_json()["reference"]

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
        response = client.post(
            "/fees/payments/gateway/verify",
            json={"reference": reference},
            headers=admin_headers,
        )

    assert response.status_code == 200
    assert response.get_json()["status"] == "confirmed"


def test_verify_gateway_payment_route_requires_auth(client):
    response = client.post("/fees/payments/gateway/verify", json={"reference": "SCH-2026-000001"})
    assert response.status_code == 401