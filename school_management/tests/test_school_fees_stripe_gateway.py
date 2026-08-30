from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import stripe as stripe_sdk

from school_app.modules.school_fees.services.gateways.stripe import StripeGateway
from school_app.modules.school_fees.services.gateways.base import (
    GatewayInitResult,
    GatewayVerifyResult,
)


@pytest.fixture
def gateway():
    return StripeGateway()


class TestStripeGatewayInitialize:

    @patch("school_app.modules.school_fees.services.gateways.stripe.stripe_sdk")
    def test_initialize_success(self, mock_stripe, app, gateway):
        """Tests successful Stripe checkout session initialization."""
        app.config["STRIPE_SECRET_KEY"] = "sk_test_12345"

        mock_session = MagicMock()
        mock_session.id = "cs_test_abc123"
        mock_session.url = "https://checkout.stripe.com/c/pay/cs_test_abc123"
        mock_stripe.checkout.Session.create.return_value = mock_session

        with app.app_context():
            result = gateway.initialize(
                amount=Decimal("150.50"),
                currency="USD",
                email="student@example.com",
                reference="FEE-2026-001",
                callback_url="https://school.com/fees/callback",
                metadata={"student_id": 42},
            )

        assert isinstance(result, GatewayInitResult)
        assert result.checkout_url == "https://checkout.stripe.com/c/pay/cs_test_abc123"
        assert result.gateway_reference == "cs_test_abc123"

        # Ensure unit amount is converted to minor units (cents: 15050)
        mock_stripe.checkout.Session.create.assert_called_once()
        create_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
        assert create_kwargs["customer_email"] == "student@example.com"
        assert create_kwargs["line_items"][0]["price_data"]["unit_amount"] == 15050
        assert create_kwargs["line_items"][0]["price_data"]["currency"] == "usd"

    def test_initialize_missing_config_key(self, app, gateway):
        """Tests exception raised when STRIPE_SECRET_KEY is missing from config."""
        app.config["STRIPE_SECRET_KEY"] = None

        with app.app_context():
            with pytest.raises(RuntimeError, match="STRIPE_SECRET_KEY is not configured"):
                gateway.initialize(
                    amount=Decimal("100.00"),
                    currency="USD",
                    email="test@example.com",
                    reference="REF-001",
                    callback_url="http://test.com",
                )

    @patch("school_app.modules.school_fees.services.gateways.stripe.stripe_sdk")
    def test_initialize_stripe_error(self, mock_stripe, app, gateway):
        """Tests handling when Stripe SDK raises a StripeError during session creation."""
        app.config["STRIPE_SECRET_KEY"] = "sk_test_12345"
        mock_stripe.error.StripeError = stripe_sdk.error.StripeError
        mock_stripe.checkout.Session.create.side_effect = stripe_sdk.error.StripeError("API connection error")

        with app.app_context():
            with pytest.raises(RuntimeError, match="Stripe initialize request failed"):
                gateway.initialize(
                    amount=Decimal("50.00"),
                    currency="USD",
                    email="test@example.com",
                    reference="REF-002",
                    callback_url="http://test.com",
                )


class TestStripeGatewayVerify:

    @patch("school_app.modules.school_fees.services.gateways.stripe.stripe_sdk")
    def test_verify_direct_lookup_by_session_id(self, mock_stripe, app, gateway):
        """Tests verifying payment using direct session ID (cs_...) lookup fast-path."""
        app.config["STRIPE_SECRET_KEY"] = "sk_test_12345"

        mock_session = MagicMock()
        mock_session.id = "cs_test_abc123"
        mock_session.payment_status = "paid"
        mock_session.amount_total = 15050
        mock_session.currency = "usd"
        mock_session.payment_intent.created = 1774534500  # Unix timestamp

        mock_stripe.checkout.Session.retrieve.return_value = mock_session

        with app.app_context():
            result = gateway.verify("cs_test_abc123")

        assert isinstance(result, GatewayVerifyResult)
        assert result.success is True
        assert result.amount == Decimal("150.50")
        assert result.currency == "USD"
        assert result.gateway_reference == "cs_test_abc123"
        assert result.paid_at is not None

        mock_stripe.checkout.Session.retrieve.assert_called_once_with(
            "cs_test_abc123", expand=["payment_intent"]
        )

    @patch("school_app.modules.school_fees.services.gateways.stripe.stripe_sdk")
    def test_verify_search_fallback_by_reference(self, mock_stripe, app, gateway):
        """Tests verifying payment by metadata reference fallback (non cs_... ref)."""
        app.config["STRIPE_SECRET_KEY"] = "sk_test_12345"

        # Search result setup
        mock_search_item = MagicMock()
        mock_search_item.id = "cs_test_found_session"
        mock_search_result = MagicMock()
        mock_search_result.data = [mock_search_item]
        mock_stripe.checkout.Session.search.return_value = mock_search_result

        # Retrieved session setup
        mock_session = MagicMock()
        mock_session.id = "cs_test_found_session"
        mock_session.payment_status = "paid"
        mock_session.amount_total = 20000
        mock_session.currency = "usd"
        mock_session.payment_intent.created = 1774534500
        mock_stripe.checkout.Session.retrieve.return_value = mock_session

        with app.app_context():
            result = gateway.verify("REF-SCHOOL-001")

        assert result.success is True
        assert result.amount == Decimal("200.00")
        mock_stripe.checkout.Session.search.assert_called_once_with(
            query="metadata['reference']:'REF-SCHOOL-001'"
        )

    @patch("school_app.modules.school_fees.services.gateways.stripe.stripe_sdk")
    def test_verify_session_not_found(self, mock_stripe, app, gateway):
        """Tests exception when no session is found for a given reference."""
        app.config["STRIPE_SECRET_KEY"] = "sk_test_12345"
        mock_stripe.error.StripeError = stripe_sdk.error.StripeError

        mock_search_result = MagicMock()
        mock_search_result.data = []
        mock_stripe.checkout.Session.search.return_value = mock_search_result

        with app.app_context():
            with pytest.raises(RuntimeError, match="no session found for reference NONEXISTENT"):
                gateway.verify("NONEXISTENT")