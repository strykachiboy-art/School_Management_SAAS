# App/routes/admin/school_fees.py

import stripe as stripe_sdk
from flask import Blueprint, jsonify, request, abort, g, current_app

from school_app.decorators import role_required
from school_app.utils.helpers import validate_request
from school_app.enums.role import Role
from school_app.models.school_fees import Payment
from school_app.modules.school_fees.requests.school_fees_request import (
    CreateFeeStructureRequest,
    UpdateFeeStructureRequest,
    GenerateInvoicesRequest,
    RecordPaymentRequest,
    InitiateGatewayPaymentRequest,
    VerifyGatewayPaymentRequest,
    ApplyDiscountRequest,
    WaiveInvoiceRequest,
    RefundPaymentRequest,
    FeeStructureResponse,
    InvoiceResponse,
    PaymentResponse,
)
from school_app.modules.school_fees.services.school_fees_service import (
    create_fee_structure,
    update_fee_structure,
    get_fee_structures_for_term,
    generate_invoices_for_term,
    get_student_invoice,
    get_student_invoices,
    record_payment,
    initiate_gateway_payment,
    confirm_gateway_payment,
    refund_payment,
    apply_discount,
    waive_invoice,
    get_outstanding_invoices,
)

school_fees_bp = Blueprint("school_fees", __name__, url_prefix="/fees")

# ====================================== fee structure routes ===============================================

@school_fees_bp.route("/structures", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(CreateFeeStructureRequest)
def create_fee_structure_route(data: CreateFeeStructureRequest):
    structure = create_fee_structure(g.user.school_id, data, actor_id=g.user.id)

    if structure is None:
        abort(400, description="Could not create fee structure")

    serialized = FeeStructureResponse.model_validate(structure).model_dump()
    return jsonify(serialized), 201


@school_fees_bp.route("/structures", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_fee_structures_route():
    classroom_id = request.args.get("classroom_id", type=int)
    session_id = request.args.get("session_id", type=int)
    term_id = request.args.get("term_id", type=int)

    if not all([classroom_id, session_id, term_id]):
        abort(400, description="classroom_id, session_id, and term_id are required")

    structures = get_fee_structures_for_term(g.user.school_id, classroom_id, session_id, term_id)
    serialized_list = [FeeStructureResponse.model_validate(s).model_dump() for s in structures]
    return jsonify(serialized_list), 200


@school_fees_bp.route("/structures/<int:structure_id>/edit", methods=["PUT", "PATCH"])
@role_required(Role.ADMIN)
@validate_request(UpdateFeeStructureRequest)
def update_fee_structure_route(data: UpdateFeeStructureRequest, structure_id):
    structure = update_fee_structure(g.user.school_id, structure_id, data, actor_id=g.user.id)

    if structure is None:
        abort(404, description="Fee structure not found")

    serialized = FeeStructureResponse.model_validate(structure).model_dump()
    return jsonify(serialized), 200


# ====================================== invoice routes ===============================================

@school_fees_bp.route("/invoices/generate", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(GenerateInvoicesRequest)
def generate_invoices_route(data: GenerateInvoicesRequest):
    try:
        invoices = generate_invoices_for_term(g.user.school_id, data, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    serialized_list = [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices]
    return jsonify({"generated": len(invoices), "invoices": serialized_list}), 201


@school_fees_bp.route("/invoices/<int:invoice_id>", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_invoice_detail_route(invoice_id):
    invoice = get_student_invoice(g.user.school_id, invoice_id)

    if g.user.role == Role.STUDENT:
        from school_app.models.student import Student
        student = Student.query.filter_by(user_id=g.user.id).first()
        if student is None or invoice.student_id != student.id:
            abort(403, description="You do not have access to this invoice")

    serialized = InvoiceResponse.model_validate(invoice).model_dump()
    return jsonify(serialized), 200


@school_fees_bp.route("/students/<int:student_id>/invoices", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def get_student_invoices_route(student_id):
    if g.user.role == Role.STUDENT:
        from school_app.models.student import Student
        student = Student.query.filter_by(user_id=g.user.id).first()
        if student is None or student.id != student_id:
            abort(403, description="You do not have access to these invoices")

    invoices = get_student_invoices(g.user.school_id, student_id)
    serialized_list = [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices]
    return jsonify(serialized_list), 200


@school_fees_bp.route("/invoices/outstanding", methods=["GET"])
@role_required(Role.ADMIN, Role.TEACHER)
def get_outstanding_invoices_route():
    session_id = request.args.get("session_id", type=int)
    term_id = request.args.get("term_id", type=int)

    if not all([session_id, term_id]):
        abort(400, description="session_id and term_id are required")

    invoices = get_outstanding_invoices(g.user.school_id, session_id, term_id)
    serialized_list = [InvoiceResponse.model_validate(inv).model_dump() for inv in invoices]
    return jsonify(serialized_list), 200


# ====================================== payment routes ===============================================

@school_fees_bp.route("/payments", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(RecordPaymentRequest)
def record_payment_route(data: RecordPaymentRequest):
    try:
        payment = record_payment(g.user.school_id, data, recorded_by=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    serialized = PaymentResponse.model_validate(payment).model_dump()
    return jsonify(serialized), 201


@school_fees_bp.route("/payments/refund", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(RefundPaymentRequest)
def refund_payment_route(data: RefundPaymentRequest):
    try:
        payment = refund_payment(g.user.school_id, data, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    serialized = PaymentResponse.model_validate(payment).model_dump()
    return jsonify(serialized), 200


@school_fees_bp.route("/payments/gateway/initiate", methods=["POST"])
@role_required(Role.ADMIN, Role.STUDENT)
@validate_request(InitiateGatewayPaymentRequest)
def initiate_gateway_payment_route(data: InitiateGatewayPaymentRequest):
    if g.user.role == Role.STUDENT:
        from school_app.models.student import Student
        student = Student.query.filter_by(user_id=g.user.id).first()
        invoice = get_student_invoice(g.user.school_id, data.invoice_id)
        if student is None or invoice.student_id != student.id:
            abort(403, description="You do not have access to this invoice")

    try:
        result = initiate_gateway_payment(g.user.school_id, data)
    except ValueError as e:
        abort(400, description=str(e))

    serialized = PaymentResponse.model_validate(result["payment"]).model_dump()
    return jsonify({
        "checkout_url": result["checkout_url"],
        "reference": result["reference"],
        "payment": serialized,
    }), 201


@school_fees_bp.route("/payments/gateway/webhook", methods=["POST"])
def gateway_webhook_route():
    body = request.get_json(silent=True) or {}
    reference = body.get("data", {}).get("reference")

    if not reference:
        abort(400, description="Missing transaction reference")

    # Webhooks are unauthenticated (no g.user), so school_id must come
    # from the payment record itself, found by reference alone.
    payment = Payment.query.filter_by(reference=reference).first()
    if payment is None:
        abort(404, description="Payment not found")

    try:
        confirm_gateway_payment(payment.school_id, reference)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"received": True}), 200


@school_fees_bp.route("/payments/gateway/stripe/webhook", methods=["POST"])
def stripe_webhook_route():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        abort(500, description="Stripe webhook secret is not configured")

    if not sig_header:
        abort(400, description="Missing Stripe-Signature header")

    try:
        event = stripe_sdk.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        abort(400, description="Invalid payload")
    except stripe_sdk.error.SignatureVerificationError:
        abort(400, description="Invalid signature")

    if event["type"] != "checkout.session.completed":
        return jsonify({"received": True, "ignored": event["type"]}), 200

    session = event["data"]["object"]
    reference = (session.get("metadata") or {}).get("reference") or session.get("client_reference_id")

    if not reference:
        abort(400, description="Missing reference in Stripe session metadata")

    payment = Payment.query.filter_by(reference=reference).first()
    if payment is None:
        abort(404, description="Payment not found")

    try:
        confirm_gateway_payment(payment.school_id, reference)
    except ValueError as e:
        abort(400, description=str(e))

    return jsonify({"received": True}), 200


@school_fees_bp.route("/payments/gateway/verify", methods=["POST"])
@role_required(Role.ADMIN, Role.STUDENT)
@validate_request(VerifyGatewayPaymentRequest)
def verify_gateway_payment_route(data: VerifyGatewayPaymentRequest):
    """Manual verification path for the frontend to poll after the
    checkout redirect, independent of whether the webhook has landed yet."""
    payment = Payment.query.filter_by(reference=data.reference).first()
    if payment is None:
        abort(404, description="Payment not found")

    if g.user.role == Role.STUDENT:
        from school_app.models.student import Student
        student = Student.query.filter_by(user_id=g.user.id).first()
        if student is None or payment.student_id != student.id:
            abort(403, description="You do not have access to this payment")

    try:
        payment = confirm_gateway_payment(g.user.school_id, data.reference)
    except ValueError as e:
        abort(400, description=str(e))

    serialized = PaymentResponse.model_validate(payment).model_dump()
    return jsonify(serialized), 200


# ====================================== discount / waiver routes ===============================================

@school_fees_bp.route("/invoices/discount", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(ApplyDiscountRequest)
def apply_discount_route(data: ApplyDiscountRequest):
    try:
        invoice = apply_discount(g.user.school_id, data, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    serialized = InvoiceResponse.model_validate(invoice).model_dump()
    return jsonify(serialized), 200


@school_fees_bp.route("/invoices/waive", methods=["POST"])
@role_required(Role.ADMIN)
@validate_request(WaiveInvoiceRequest)
def waive_invoice_route(data: WaiveInvoiceRequest):
    try:
        invoice = waive_invoice(g.user.school_id, data, actor_id=g.user.id)
    except ValueError as e:
        abort(400, description=str(e))

    serialized = InvoiceResponse.model_validate(invoice).model_dump()
    return jsonify(serialized), 200