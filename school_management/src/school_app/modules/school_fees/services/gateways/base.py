# services/school_fees_payment/gateways/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class GatewayInitResult:
    """Returned when a gateway checkout session is successfully started."""
    checkout_url: str
    gateway_reference: str
    raw_response: dict


@dataclass
class GatewayVerifyResult:
    """Returned when verifying a transaction's real status with the gateway."""
    success: bool
    gateway_reference: str
    amount: Decimal
    currency: str
    paid_at: Optional[str]
    raw_response: dict


class PaymentGateway(ABC):
    name: str
    @abstractmethod
    def initialize(
        self,
        *,
        amount: Decimal,
        currency: str,
        email: str,
        reference: str,
        callback_url: str,
        metadata: Optional[dict] = None,
    ) -> GatewayInitResult:
        raise NotImplementedError

    @abstractmethod
    def verify(self, reference: str) -> GatewayVerifyResult:
        raise NotImplementedError