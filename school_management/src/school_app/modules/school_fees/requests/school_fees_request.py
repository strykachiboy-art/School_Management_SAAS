# requests/school_fees.py

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

from school_app.enums.school_fees import (
    FeeCategory, PaymentMethod, PaymentStatus, InvoiceStatus, PaymentGateway
)

MAX_SANE_AMOUNT = Decimal("10000000")


class CreateFeeStructureRequest(BaseModel):
    classroom_id: int
    session_id: int
    term_id: int
    category: FeeCategory
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_mandatory: bool = True

    @field_validator("amount")
    @classmethod
    def amount_must_be_reasonable(cls, v: Decimal) -> Decimal:
        if v > MAX_SANE_AMOUNT:
            raise ValueError("amount exceeds sane fee limit")
        return v


class UpdateFeeStructureRequest(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    is_mandatory: Optional[bool] = None


class GenerateInvoicesRequest(BaseModel):
    classroom_id: int
    session_id: int
    term_id: int
    due_date: Optional[date] = None


class RecordPaymentRequest(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    payment_method: PaymentMethod


class ApplyDiscountRequest(BaseModel):
    invoice_id: int
    discount_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: Optional[str] = Field(default=None, max_length=255)


class WaiveInvoiceRequest(BaseModel):
    invoice_id: int
    reason: str = Field(min_length=1, max_length=255)


class RefundPaymentRequest(BaseModel):
    payment_id: int
    refund_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=1, max_length=255)


class InitiateGatewayPaymentRequest(BaseModel):
    invoice_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    gateway: PaymentGateway
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    email: str
    callback_url: str


class VerifyGatewayPaymentRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class FeeStructureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    classroom_id: int
    session_id: int
    term_id: int
    category: FeeCategory
    amount: float
    is_mandatory: bool
    created_at: datetime


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: FeeCategory
    amount: float


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    session_id: int
    term_id: int
    total_amount: float
    discount_amount: float
    final_amount: float
    waived_amount: float
    amount_paid: float
    balance: float
    status: InvoiceStatus
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItemResponse] = []


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    student_id: int
    amount: float
    currency: str
    payment_method: PaymentMethod
    status: PaymentStatus
    reference: str
    recorded_by: Optional[int] = None
    gateway: Optional[PaymentGateway] = None
    gateway_reference: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    refund_amount: Optional[float] = None
    refund_reason: Optional[str] = None
    refunded_at: Optional[datetime] = None
    refunded_by: Optional[int] = None