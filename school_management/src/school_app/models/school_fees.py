# models/school_fees.py

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Boolean,
    ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.hybrid import hybrid_property

from school_app.extensions import db
from school_app.enums.school_fees import (
    FeeCategory, PaymentMethod, PaymentStatus, InvoiceStatus, PaymentGateway
)


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


Money = Numeric(12, 2)


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_fee_structures_amount_nonneg"),
        UniqueConstraint(
            "school_id", "classroom_id", "session_id", "term_id", "category",
            name="uq_fee_structure_per_school",
        ), {"extend_existing": True}
    )

    id = Column(Integer, primary_key=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classroom_id = Column(Integer, ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id", ondelete="CASCADE"), nullable=False)
    category = Column(SQLEnum(FeeCategory), nullable=False)
    amount = Column(Money, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("fee_structures", lazy="dynamic"))


class Invoice(db.Model):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="ck_invoices_total_amount_nonneg"),
        CheckConstraint("discount_amount >= 0", name="ck_invoices_discount_amount_nonneg"),
        CheckConstraint("waived_amount >= 0", name="ck_invoices_waived_amount_nonneg"),
        CheckConstraint("amount_paid >= 0", name="ck_invoices_amount_paid_nonneg"),
        CheckConstraint(
            "discount_amount + waived_amount <= total_amount",
            name="ck_invoices_discount_waived_le_total",
        ),
    )

    id = Column(Integer, primary_key=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(Integer, ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id", ondelete="CASCADE"), nullable=False)
    total_amount = Column(Money, nullable=False)
    discount_amount = Column(Money, nullable=False, default=Decimal("0.00"))
    waived_amount = Column(Money, nullable=False, default=Decimal("0.00"))

    amount_paid = Column(Money, default=Decimal("0.00"), nullable=False)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.UNPAID, nullable=False)
    due_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("invoices", lazy="dynamic"))
    items = db.relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")

    @hybrid_property
    def final_amount(self):
        return self.total_amount - self.discount_amount

    @hybrid_property
    def balance(self):
        return self.final_amount - self.waived_amount - self.amount_paid


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_invoice_items_amount_nonneg"),
    )

    id = Column(Integer, primary_key=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    category = Column(SQLEnum(FeeCategory), nullable=False)
    amount = Column(Money, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("invoice_items", lazy="dynamic"))
    invoice = db.relationship("Invoice", back_populates="items")


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonneg"),
        CheckConstraint(
            "refund_amount IS NULL OR refund_amount >= 0",
            name="ck_payments_refund_amount_nonneg",
        ),
    )

    id = Column(Integer, primary_key=True)
    school_id = Column(
        Integer,
        ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Money, nullable=False)
    payment_method = Column(SQLEnum(PaymentMethod), nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    reference = Column(String(120), nullable=False, unique=True)
    recorded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # --- gateway support ---
    currency = Column(String(3), nullable=False, default="USD")
    gateway = Column(SQLEnum(PaymentGateway), nullable=True)
    gateway_reference = Column(String(120), nullable=True, unique=True)
    paid_at = Column(DateTime, nullable=True)

    refund_amount = Column(Money, nullable=True)
    refund_reason = Column(String(255), nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    refunded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    school = db.relationship("School", backref=db.backref("payments", lazy="dynamic"))
    invoice = db.relationship("Invoice", back_populates="payments")