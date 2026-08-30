# services/school_fees_payment/gateways/stripe.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import stripe as stripe_sdk
from flask import current_app

from school_app.modules.school_fees.services.gateways.base import (
    PaymentGateway,
    GatewayInitResult,
    GatewayVerifyResult,
)

DEFAULT_TIMEOUT = 10  # seconds — matches Paystack gateway's convention


class StripeGateway(PaymentGateway):
    name = "stripe"

    def _client(self) -> stripe_sdk:
        key = current_app.config.get("STRIPE_SECRET_KEY")
        if not key:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured")
        stripe_sdk.api_key = key
        stripe_sdk.max_network_retries = 2
        return stripe_sdk

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
        client = self._client()
        amount_minor_units = int(amount * 100)

        try:
            session = client.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                customer_email=email,
                client_reference_id=reference,
                line_items=[{
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount_minor_units,
                        "product_data": {"name": f"School fees payment {reference}"},
                    },
                    "quantity": 1,
                }],
                success_url=f"{callback_url}?reference={reference}",
                cancel_url=f"{callback_url}?reference={reference}&cancelled=1",
                metadata={**(metadata or {}), "reference": reference},
            )
        except stripe_sdk.error.StripeError as exc:
            raise RuntimeError(f"Stripe initialize request failed: {exc}") from exc

        if not session.url:
            raise RuntimeError("Stripe initialize failed: no checkout URL returned")

        return GatewayInitResult(
            checkout_url=session.url,
            gateway_reference=session.id,
            raw_response=session,
        )

    def verify(self, reference: str) -> GatewayVerifyResult:
        client = self._client()
        session = None

        # Fast-path direct lookup if given a Stripe Session ID (cs_...)
        if reference.startswith("cs_"):
            try:
                session = client.checkout.Session.retrieve(
                    reference, expand=["payment_intent"]
                )
            except stripe_sdk.error.StripeError:
                session = None

        # Fallback to Search API via domain reference if direct lookup was not used or failed
        if not session:
            try:
                results = client.checkout.Session.search(
                    query=f"metadata['reference']:'{reference}'"
                )
                if not results.data:
                    raise RuntimeError(f"Stripe verify failed: no session found for reference {reference}")

                session = client.checkout.Session.retrieve(
                    results.data[0].id, expand=["payment_intent"]
                )
            except stripe_sdk.error.StripeError as exc:
                raise RuntimeError(f"Stripe verify request failed: {exc}") from exc

        success = session.payment_status == "paid"
        amount_minor_units = Decimal(str(session.amount_total or 0))
        paid_at = None

        if session.payment_intent and getattr(session.payment_intent, "created", None):
            paid_at = datetime.fromtimestamp(
                session.payment_intent.created, tz=timezone.utc
            ).isoformat()

        return GatewayVerifyResult(
            success=success,
            gateway_reference=session.id,
            amount=amount_minor_units / Decimal("100"),
            currency=(session.currency or "usd").upper(),
            paid_at=paid_at,
            raw_response=session,
        )