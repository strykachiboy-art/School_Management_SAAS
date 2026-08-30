# services/school_fees_payment/gateways/paystack.py
from __future__ import annotations

from decimal import Decimal
from typing import Optional

import requests
from flask import current_app

from school_app.modules.school_fees.services.gateways.base import (
    PaymentGateway,
    GatewayInitResult,
    GatewayVerifyResult,
)

PAYSTACK_BASE_URL = "https://api.paystack.co"
DEFAULT_TIMEOUT = 10  # seconds — never let a gateway call hang the worker


class PaystackGateway(PaymentGateway):
    name = "paystack"

    def _secret_key(self) -> str:
        key = current_app.config.get("PAYSTACK_SECRET_KEY")
        if not key:
            raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")
        return key

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._secret_key()}",
            "Content-Type": "application/json",
        }

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
        amount_minor_units = int(amount * 100)

        payload = {
            "amount": amount_minor_units,
            "currency": currency,
            "email": email,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata or {},
        }

        try:
            response = requests.post(
                f"{PAYSTACK_BASE_URL}/transaction/initialize",
                json=payload,
                headers=self._headers(),
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Paystack initialize request failed: {exc}") from exc

        body = response.json()
        if not response.ok or not body.get("status"):
            raise RuntimeError(
                f"Paystack initialize failed: {body.get('message', 'unknown error')}"
            )

        data = body["data"]
        return GatewayInitResult(
            checkout_url=data["authorization_url"],
            gateway_reference=data["reference"],
            raw_response=body,
        )

    def verify(self, reference: str) -> GatewayVerifyResult:
        try:
            response = requests.get(
                f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
                headers=self._headers(),
                timeout=DEFAULT_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Paystack verify request failed: {exc}") from exc

        body = response.json()
        if not response.ok or not body.get("status"):
            raise RuntimeError(
                f"Paystack verify failed: {body.get('message', 'unknown error')}"
            )

        data = body["data"]
        success = data.get("status") == "success"
        amount_minor_units = Decimal(str(data.get("amount", 0)))

        return GatewayVerifyResult(
            success=success,
            gateway_reference=data["reference"],
            amount=amount_minor_units / Decimal("100"),
            currency=data.get("currency", "NGN"),
            paid_at=data.get("paid_at"),
            raw_response=body,
        )