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

def create_fee_structure(school_id: int, payload: CreateFeeStructureRequest, actor_id=None) -> FeeStructure:
    structure = FeeStructure(school_id=school_id, **payload.model_dump())
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


def update_fee_structure(school_id: int, structure_id: int, payload: UpdateFeeStructureRequest, actor_id=None) -> FeeStructure:
    structure = FeeStructure.query.filter_by(id=structure_id, school_id=school_id).first()
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


def get_fee_structures_for_term(school_id: int, classroom_id: int, session_id: int, term_id: int) -> List[FeeStructure]:
    return FeeStructure.query.filter_by(
        school_id=school_id, classroom_id=classroom_id, session_id=session_id, term_id=term_id
    ).all()


# ---------- Invoice Generation ----------

def generate_invoices_for_term(school_id: int, payload: GenerateInvoicesRequest, actor_id=None) -> List[Invoice]:
    from school_app.models.student import Student 

    structures = get_fee_structures_for_term(
        school_id, payload.classroom_id, payload.session_id, payload.term_id
    )
    if not structures:
        raise ValueError("No fee structure defined for this classroom/session/term")

    students = Student.query.filter_by(school_id=school_id, classroom_id=payload.classroom_id).all()
    if not students:
        raise ValueError("No students found in this classroom")

    total_amount = sum((s.amount for s in structures), Decimal("0.00"))
    invoices = []

    for student in students:
        existing = Invoice.query.filter_by(
            school_id=school_id,
            student_id=student.id,
            session_id=payload.session_id,
            term_id=payload.term_id,
        ).first()
        if existing:
            continue  

        invoice = Invoice(
            school_id=school_id,
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
            InvoiceItem(school_id=school_id, category=s.category, amount=s.amount) for s in structures
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


def get_student_invoice(school_id: int, invoice_id: int) -> Invoice:
    invoice = Invoice.query.filter_by(id=invoice_id, school_id=school_id).first()
    if invoice is None:
        abort(404, description="Invoice not found")
    return invoice


def get_student_invoices(school_id: int, student_id: int) -> List[Invoice]:
    return Invoice.query.filter_by(school_id=school_id, student_id=student_id).order_by(Invoice.created_at.desc()).all()


# ---------- Discounts & Waivers ----------

def apply_discount(school_id: int, payload: ApplyDiscountRequest, actor_id) -> Invoice:
    invoice = get_student_invoice(school_id, payload.invoice_id)

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


def waive_invoice(school_id: int, payload: WaiveInvoiceRequest, actor_id) -> Invoice:
    invoice = get_student_invoice(school_id, payload.invoice_id)

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

def _get_invoice_recipient_user_ids(school_id: int, invoice: Invoice) -> List[int]:
    from school_app.models.student import Student
    from school_app.models.parent_guardian import ParentGuardian, ParentGuardianStudent

    student = Student.query.filter_by(id=invoice.student_id, school_id=school_id).first()
    if not student:
        return []
    
    recipient_user_ids = [student.user_id]

    guardian_links = ParentGuardianStudent.query.filter_by(student_id=invoice.student_id).all()
    guardian_ids = [link.parent_guardian_id for link in guardian_links]

    if guardian_ids:
        guardians = ParentGuardian.query.filter(ParentGuardian.id.in_(guardian_ids), ParentGuardian.school_id == school_id).all()
        recipient_user_ids.extend(g.user_id for g in guardians)

    return recipient_user_ids


def _generate_payment_reference(school_id: int) -> str:
    year = date.today().year
    count_this_year = Payment.query.filter(
        Payment.school_id == school_id,
        Payment.reference.like(f"SCH-{year}-%")
    ).count()
    return f"SCH-{year}-{count_this_year + 1:06d}"


def _apply_confirmed_payment_to_invoice(school_id: int, invoice: Invoice, payment: Payment, actor_id=None) -> None:
    status_before = invoice.status
    amount_paid_before = invoice.amount_paid

    invoice.amount_paid += payment.amount
    invoice.status = (
        InvoiceStatus.PAID if invoice.balance <= 0 else InvoiceStatus.PARTIAL
    )

    db.session.flush()

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

    for recipient_id in _get_invoice_recipient_user_ids(school_id, invoice):
        notify_user(
            recipient_id=recipient_id,
            title="Payment Received",
            message=f"Payment of {payment.amount} recorded against your fees.",
            notification_type=NotificationType.SCHOOL_FEES,
        )


def record_payment(school_id: int, payload: RecordPaymentRequest, recorded_by=None) -> Payment:
    invoice = Invoice.query.filter_by(id=payload.invoice_id, school_id=school_id).first()
    if invoice is None:
        abort(404, description="Invoice not found")

    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.WAIVED):
        raise ValueError(f"Cannot record payment against a {invoice.status.value} invoice")

    remaining = invoice.balance
    if payload.amount > remaining:
        raise ValueError(f"Payment exceeds outstanding balance of {remaining}")

    for attempt in range(2):
        reference = _generate_payment_reference(school_id)
        payment = Payment(
            school_id=school_id,
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

    _apply_confirmed_payment_to_invoice(school_id, invoice, payment, actor_id=recorded_by)
    return payment


def initiate_gateway_payment(school_id: int, payload: InitiateGatewayPaymentRequest) -> dict:
    invoice = Invoice.query.filter_by(id=payload.invoice_id, school_id=school_id).first()
    if invoice is None:
        abort(404, description="Invoice not found")

    if invoice.status in (InvoiceStatus.CANCELLED, InvoiceStatus.WAIVED):
        raise ValueError(f"Cannot pay a {invoice.status.value} invoice")

    remaining = invoice.balance
    if payload.amount > remaining:
        raise ValueError(f"Payment exceeds outstanding balance of {remaining}")

    for attempt in range(2):
        reference = _generate_payment_reference(school_id)
        payment = Payment(
            school_id=school_id,
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
            metadata={"invoice_id": invoice.id, "student_id": invoice.student_id, "school_id": school_id},
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


def confirm_gateway_payment(school_id: int, reference: str) -> Payment:
    payment = Payment.query.filter_by(reference=reference, school_id=school_id).first()
    if payment is None:
        abort(404, description="Payment not found")

    if payment.status == PaymentStatus.CONFIRMED:
        return payment  

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

    invoice = Invoice.query.filter_by(id=payment.invoice_id, school_id=school_id).first()
    if invoice is None:
        abort(404, description="Invoice not found")

    payment.status = PaymentStatus.CONFIRMED
    payment.gateway_reference = result.gateway_reference
    payment.paid_at = (
        datetime.fromisoformat(result.paid_at) if result.paid_at else _utcnow()
    )
    db.session.flush()

    _apply_confirmed_payment_to_invoice(school_id, invoice, payment, actor_id=None)
    return payment


def refund_payment(school_id: int, payload: RefundPaymentRequest, actor_id) -> Payment:
    payment = Payment.query.filter_by(id=payload.payment_id, school_id=school_id).first()
    if payment is None:
        abort(404, description="Payment not found")

    if payment.status != PaymentStatus.CONFIRMED:
        raise ValueError(f"Cannot refund a payment with status {payment.status.value}")

    if payload.refund_amount > payment.amount:
        raise ValueError(f"Refund amount exceeds original payment of {payment.amount}")

    invoice = Invoice.query.filter_by(id=payment.invoice_id, school_id=school_id).first()

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


def get_outstanding_invoices(school_id: int, session_id: int, term_id: int) -> List[Invoice]:
    return Invoice.query.filter(
        Invoice.school_id == school_id,
        Invoice.session_id == session_id,
        Invoice.term_id == term_id,
        Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]),
    ).all()


def mark_overdue_invoices(school_id: int, as_of: date = None) -> int:
    as_of = as_of or date.today()
    overdue = Invoice.query.filter(
        Invoice.school_id == school_id,
        Invoice.due_date < as_of,
        Invoice.status.in_([InvoiceStatus.UNPAID, InvoiceStatus.PARTIAL]),
    ).all()
    for invoice in overdue:
        invoice.status = InvoiceStatus.OVERDUE
    db.session.commit()
    return len(overdue)