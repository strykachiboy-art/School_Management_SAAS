# services/school_fees_payment/gateways/__init__.py
from school_app.enums.school_fees import PaymentGateway as PaymentGatewayEnum
from school_app.modules.school_fees.services.gateways.base import PaymentGateway
from school_app.modules.school_fees.services.gateways.paystack import PaystackGateway
from school_app.modules.school_fees.services.gateways.stripe import StripeGateway

_GATEWAYS: dict[PaymentGatewayEnum, PaymentGateway] = {
    PaymentGatewayEnum.PAYSTACK: PaystackGateway(),
    PaymentGatewayEnum.STRIPE: StripeGateway(),
}


def get_gateway(gateway: PaymentGatewayEnum) -> PaymentGateway:
    try:
        return _GATEWAYS[gateway]
    except KeyError:
        raise ValueError(f"Unsupported payment gateway: {gateway}")