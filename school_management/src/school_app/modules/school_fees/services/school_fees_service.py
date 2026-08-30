# services/school_fees.py
from __future__ import annotations
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List

from flask import abort
from sqlalchemy.exc import IntegrityError
from school_app.extensions import db
from school_app.models.school_fees import FeeStructure, Invoice, InvoiceItem, Payment
from school_app.enums.school_fees import InvoiceStatus, PaymentStatus, PaymentMethod
from school_app.enums.audit import AuditAction
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.modules.school_fees.services.gateways import get_gateway
from school_app.modules.school_fees.requests.school_fees_request import (
    CreateFeeStructureRequest,
    UpdateFeeStructureRequest,
    GenerateInvoicesRequest,
    RecordPaymentRequest,
    InitiateGatewayPaymentRequest,
    ApplyDiscountRequest,
    WaiveInvoiceRequest,
    RefundPaymentRequest,
)


def _utcnow():
    return datetime.now(timezone.utc)


# ---------- Fee Structure ----------

def create_fee_structure(payload: CreateFeeStructureRequest, actor_id=None) -> FeeStructure:
    structure = FeeStructure(**payload.model_dump())
    db.session.add(structure)
    db.session.flush() 

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="FeeStructure",
            resource_id=structure.id,
            description=f"Created fee structure: {structure.category.value} amount={structure.amount}",
        )

    db.session.commit()
    return structure


def update_fee_structure(structure_id: int, payload: UpdateFeeStructureRequest, actor_id=None) -> FeeStructure:
    structure = db.session.get(FeeStructure, structure_id)
    if structure is None:
        return None

    data = payload.model_dump(exclude_unset=True)
    changes = {}
    for field, value in data.items():
        old_value = getattr(structure, field)
        if value != old_value:
            changes[field] = {"before": str(old_value), "after": str(value)}
        setattr(structure, field, value)

    db.session.flush()

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="FeeStructure",
            resource_id=structure.id,
            description=f"Updated fee structure {structure.id}",
            changes=changes,
        )

    db.session.commit()
    return structure


def get_fee_structures_for_term(classroom_id: int, session_id: int, term_id: int) -> List[FeeStructure]:
    return FeeStructure.query.filter_by(
        classroom_id=classroom_id, session_id=session_id, term_id=term_id
    ).all()


# ---------- Invoice Generation ----------

def generate_invoices_for_term(payload: GenerateInvoicesRequest, actor_id=None) -> List[Invoice]:
    from school_app.models.student import Student 

    structures = get_fee_structures_for_term(
        payload.classroom_id, payload.session_id, payload.term_id
    )
    if not structures:
        raise ValueError("No fee structure defined for this classroom/session/term")

    students = Student.query.filter_by(classroom_id=payload.classroom_id).all()
    if not students:
        raise ValueError("No students found in this classroom")

    total_amount = sum((s.amount for s in structures), Decimal("0.00"))
    invoices = []

    for student in students:
        existing = Invoice.query.filter_by(
            student_id=student.id,
            session_id=payload.session_id,
            term_id=payload.term_id,
        ).first()
        if existing:
            continue  

        invoice = Invoice(
            student_id=student.id,
            session_id=payload.session_id,
            term_id=payload.term_id,
            total_amount=total_amount,
            discount_amount=Decimal("0.00"),
            waived_amount=Decimal("0.00"),
            amount_paid=Decimal("0.00"),
            due_date=payload.due_date,
        )
        invoice.items = [
            InvoiceItem(category=s.category, amount=s.amount) for s in structures
        ]
        db.session.add(invoice)
        invoices.append(invoice)

    db.session.flush()

    if actor_id and invoices:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.BULK_ACTION,
            resource_type="Invoice",
            resource_id=payload.classroom_id,
            description=(
                f"Bulk generated {len(invoices)} invoice(s) for classroom={payload.classroom_id} "
                f"session={payload.session_id} term={payload.term_id}"
            ),
            changes={"invoice_ids": [inv.id for inv in invoices]},
        )

    db.session.commit()
    return invoices


def get_student_invoice(invoice_id: int) -> Invoice:
    invoice = db.session.get(Invoice, invoice_id)
    if invoice is None:
        abort(404, description="Invoice not found")
    return invoice


def get_student_invoices(student_id: int) -> List[Invoice]:
    return Invoice.query.filter_by(student_id=student_id).order_by(Invoice.created_at.desc()).all()


# ---------- Discounts & Waivers ----------

def apply_discount(payload: ApplyDiscountRequest, actor_id) -> Invoice:
    """Reduce what's owed on an invoice without touching the original
    total_amount, so the original bill stays auditable (blueprint §8)."""
    invoice = get_student_invoice(payload.invoice_id)

    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.WAIVED):
        raise ValueError(f"Cannot apply a discount to a {invoice.status.value} invoice")

    if payload.discount_amount + invoice.waived_amount > invoice.total_amount:
        raise ValueError("Discount would exceed the invoice's total amount")

    discount_before = invoice.discount_amount
    invoice.discount_amount = payload.discount_amount

    if invoice.balance <= 0:
        invoice.status = InvoiceStatus.PAID
    elif invoice.amount_paid > 0:
        invoice.status = InvoiceStatus.PARTIAL

    db.session.flush()

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.DISCOUNT_APPLIED,
        resource_type="Invoice",
        resource_id=invoice.id,
        description=f"Applied discount to invoice {invoice.id}" + (f": {payload.reason}" if payload.reason else ""),
        changes={"discount_amount": {"before": str(discount_before), "after": str(invoice.discount_amount)}},
    )

    db.session.commit()
    return invoice


def waive_invoice(payload: WaiveInvoiceRequest, actor_id) -> Invoice:
    """Forgive the remaining balance on an invoice. Admin-only, audited —
    see role_required(Role.ADMIN) on the route (blueprint §9)."""
    invoice = get_student_invoice(payload.invoice_id)

    if invoice.status == InvoiceStatus.CANCELLED:
        raise ValueError("Cannot waive a cancelled invoice")

    remaining = invoice.final_amount - invoice.amount_paid
    if remaining <= 0:
        raise ValueError("Invoice has no remaining balance to waive")

    waived_before = invoice.waived_amount
    invoice.waived_amount = invoice.waived_amount + remaining
    invoice.status = InvoiceStatus.WAIVED

    db.session.flush()

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.FEE_WAIVED,
        resource_type="Invoice",
        resource_id=invoice.id,
        description=f"Waived invoice {invoice.id}: {payload.reason}",
        changes={"waived_amount": {"before": str(waived_before), "after": str(invoice.waived_amount)}},
    )

    db.session.commit()
    return invoice


# ---------- Payments ----------

def _get_invoice_recipient_user_ids(invoice: Invoice) -> List[int]:
    from school_app.models.student import Student
    from school_app.models.parent_guardian import ParentGuardian, ParentGuardianStudent

    student = db.session.get(Student, invoice.student_id)
    recipient_user_ids = [student.user_id]

    guardian_links = ParentGuardianStudent.query.filter_by(student_id=invoice.student_id).all()
    guardian_ids = [link.parent_guardian_id for link in guardian_links]

    if guardian_ids:
        guardians = ParentGuardian.query.filter(ParentGuardian.id.in_(guardian_ids)).all()
        recipient_user_ids.extend(g.user_id for g in guardians)

    return recipient_user_ids


def _generate_payment_reference() -> str:
    """Server-generated, unique payment reference — never trust a
    client-supplied value (blueprint §4). Format: SCH-<year>-<seq>.
    The DB's UNIQUE constraint on Payment.reference is the actual
    safety net; this count is just for a readable, mostly-sequential
    number and is retried on the rare collision.
    """
    year = date.today().year
    count_this_year = Payment.query.filter(
        Payment.reference.like(f"SCH-{year}-%")
    ).count()
    return f"SCH-{year}-{count_this_year + 1:06d}"


def _apply_confirmed_payment_to_invoice(invoice: Invoice, payment: Payment, actor_id=None) -> None:
    """Shared by both the offline (record_payment) and gateway
    (confirm_gateway_payment) paths — bumps amount_paid, flips invoice
    status, writes the audit log, and notifies student + guardians.
    Called only once a payment is actually CONFIRMED.
    """
    status_before = invoice.status
    amount_paid_before = invoice.amount_paid

    invoice.amount_paid += payment.amount
    invoice.status = (
        InvoiceStatus.PAID if invoice.balance <= 0 else InvoiceStatus.PARTIAL
    )

    db.session.flush()

    # actor_id is None for gateway-confirmed payments (webhook, no
    # logged-in user) — AuditLog.actor_id is now nullable, so this
    # writes fine either way.
    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.CREATE,
        resource_type="Payment",
        resource_id=payment.id,
        description=f"Applied payment of {payment.amount} against invoice {invoice.id}",
        changes={
            "amount_paid": {"before": str(amount_paid_before), "after": str(invoice.amount_paid)},
            "status": {"before": status_before.value, "after": invoice.status.value},
        },
    )

    db.session.commit()

    from school_app.modules.notifications.services.notification_service import notify_user
    from school_app.enums.notification import NotificationType

    for recipient_id in _get_invoice_recipient_user_ids(invoice):
        notify_user(
            recipient_id=recipient_id,
            title="Payment Received",
            message=f"Payment of {payment.amount} recorded against your fees.",
            notification_type=NotificationType.SCHOOL_FEES,
        )


def record_payment(payload: RecordPaymentRequest, recorded_by=None) -> Payment:
    """Offline payments only (cash, bank transfer, cheque recorded by an
    admin) — confirmed immediately since there's no gateway to verify
    against. For card/online payments, use initiate_gateway_payment +
    confirm_gateway_payment instead.
    """
    invoice = db.session.get(Invoice, payload.invoice_id)
    if invoice is None:
        abort(404, description="Invoice not found")

    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.WAIVED):
        raise ValueError(f"Cannot record payment against a {invoice.status.value} invoice")

    remaining = invoice.balance
    if payload.amount > remaining:
        raise ValueError(f"Payment exceeds outstanding balance of {remaining}")

    # Retry once on the (very unlikely) reference collision, since the
    # sequential count above isn't atomic under concurrent requests.
    for attempt in range(2):
        reference = _generate_payment_reference()
        payment = Payment(
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            amount=payload.amount,
            currency="NGN",
            payment_method=payload.payment_method,
            reference=reference,
            recorded_by=recorded_by,
            status=PaymentStatus.CONFIRMED,
        )
        db.session.add(payment)
        try:
            db.session.flush()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 1:
                raise

    _apply_confirmed_payment_to_invoice(invoice, payment, actor_id=recorded_by)
    return payment


def initiate_gateway_payment(payload: InitiateGatewayPaymentRequest) -> dict:
    """Start a hosted checkout session. Creates a PENDING Payment row
    (no recorded_by — nobody's recording it, the payer is doing it
    themselves) and does NOT touch invoice.amount_paid — that only
    happens once confirm_gateway_payment verifies the transaction.
    Returns the checkout URL for the frontend to redirect to.
    """
    invoice = db.session.get(Invoice, payload.invoice_id)
    if invoice is None:
        abort(404, description="Invoice not found")

    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.WAIVED):
        raise ValueError(f"Cannot pay a {invoice.status.value} invoice")

    remaining = invoice.balance
    if payload.amount > remaining:
        raise ValueError(f"Payment exceeds outstanding balance of {remaining}")

    for attempt in range(2):
        reference = _generate_payment_reference()
        payment = Payment(
            invoice_id=invoice.id,
            student_id=invoice.student_id,
            amount=payload.amount,
            currency=payload.currency,
            payment_method=PaymentMethod.ONLINE,
            reference=reference,
            recorded_by=None,
            gateway=payload.gateway,
            status=PaymentStatus.PENDING,
        )
        db.session.add(payment)
        try:
            db.session.flush()
            break
        except IntegrityError:
            db.session.rollback()
            if attempt == 1:
                raise

    gateway = get_gateway(payload.gateway)
    try:
        result = gateway.initialize(
            amount=payload.amount,
            currency=payload.currency,
            email=payload.email,
            reference=reference,
            callback_url=payload.callback_url,
            metadata={"invoice_id": invoice.id, "student_id": invoice.student_id},
        )
    except RuntimeError as e:
        payment.status = PaymentStatus.FAILED
        db.session.flush()
        create_audit_log(
            actor_id=None,
            action=AuditAction.PAYMENT_FAILED,
            resource_type="Payment",
            resource_id=payment.id,
            description=f"Gateway initialize failed for invoice {invoice.id}: {e}",
        )
        db.session.commit()
        raise ValueError(str(e))

    payment.gateway_reference = result.gateway_reference
    db.session.commit()

    return {"checkout_url": result.checkout_url, "reference": reference, "payment": payment}


def confirm_gateway_payment(reference: str) -> Payment:
    """Called from the webhook/callback route. Never trusts the webhook
    payload's own status field — always re-verifies with the gateway
    directly before touching the invoice. Idempotent: a payment already
    CONFIRMED is returned as-is rather than double-applied.
    """
    payment = Payment.query.filter_by(reference=reference).first()
    if payment is None:
        abort(404, description="Payment not found")

    if payment.status == PaymentStatus.CONFIRMED:
        return payment  # already applied — webhook fired more than once

    if payment.gateway is None:
        raise ValueError("Payment has no associated gateway")

    gateway = get_gateway(payment.gateway)
    result = gateway.verify(reference)

    if not result.success:
        payment.status = PaymentStatus.FAILED
        db.session.flush()
        create_audit_log(
            actor_id=None,
            action=AuditAction.PAYMENT_FAILED,
            resource_type="Payment",
            resource_id=payment.id,
            description=f"Gateway did not confirm payment {payment.id} (reference={reference}) as successful",
        )
        db.session.commit()
        raise ValueError("Gateway did not confirm this payment as successful")

    invoice = db.session.get(Invoice, payment.invoice_id)
    if invoice is None:
        abort(404, description="Invoice not found")

    payment.status = PaymentStatus.CONFIRMED
    payment.gateway_reference = result.gateway_reference
    payment.paid_at = (
        datetime.fromisoformat(result.paid_at) if result.paid_at else _utcnow()
    )
    db.session.flush()

    _apply_confirmed_payment_to_invoice(invoice, payment, actor_id=None)
    return payment


def refund_payment(payload: RefundPaymentRequest, actor_id) -> Payment:
    """Refunds annotate the original payment rather than deleting it,
    preserving financial history (blueprint §10)."""
    payment = db.session.get(Payment, payload.payment_id)
    if payment is None:
        abort(404, description="Payment not found")

    if payment.status != PaymentStatus.CONFIRMED:
        raise ValueError(f"Cannot refund a payment with status {payment.status.value}")

    if payload.refund_amount > payment.amount:
        raise ValueError(f"Refund amount exceeds original payment of {payment.amount}")

    invoice = db.session.get(Invoice, payment.invoice_id)

    payment.status = PaymentStatus.REFUNDED
    payment.refund_amount = payload.refund_amount
    payment.refund_reason = payload.reason
    payment.refunded_at = _utcnow()
    payment.refunded_by = actor_id

    amount_paid_before = invoice.amount_paid
    status_before = invoice.status
    invoice.amount_paid = invoice.amount_paid - payload.refund_amount
    if invoice.amount_paid <= 0:
        invoice.status = InvoiceStatus.UNPAID
    elif invoice.balance > 0:
        invoice.status = InvoiceStatus.PARTIAL

    db.session.flush()

    create_audit_log(
        actor_id=actor_id,
        action=AuditAction.PAYMENT_REFUNDED,
        resource_type="Payment",
        resource_id=payment.id,
        description=f"Refunded {payload.refund_amount} on payment {payment.id}: {payload.reason}",
        changes={
            "invoice_amount_paid": {"before": str(amount_paid_before), "after": str(invoice.amount_paid)},
            "invoice_status": {"before": status_before.value, "after": invoice.status.value},
        },
    )

    db.session.commit()
    return payment


def get_outstanding_invoices(session_id: int, term_id: int) -> List[Invoice]:
    return Invoice.query.filter(
        Invoice.session_id == session_id,
        Invoice.term_id == term_id,
        Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]),
    ).all()


def mark_overdue_invoices(as_of: date = None) -> int:
    as_of = as_of or date.today()
    overdue = Invoice.query.filter(
        Invoice.due_date < as_of,
        Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL]),
    ).all()
    for invoice in overdue:
        invoice.status = InvoiceStatus.OVERDUE
    db.session.commit()
    return len(overdue)