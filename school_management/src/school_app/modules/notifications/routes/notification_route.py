from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from school_app.extensions import db, limiter
from pydantic import ValidationError

from school_app.decorators import role_required
from school_app.enums.role import Role
from school_app.models.user import User
from school_app.modules.notifications.requests.notification_request import CreateNotificationRequest
from school_app.modules.notifications.services.notification_service import (
    create_notification,
    get_notification,
    get_my_notifications,
    get_unread_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    delete_notification,
    InvalidRecipientError,
)

notification_bp = Blueprint("notification", __name__, url_prefix="/notifications")

MAX_PER_PAGE = 100


def serialize_notification(n):
    return {
        "id": n.id,
        "recipient_id": n.recipient_id,
        "title": n.title,
        "message": n.message,
        "notification_type": n.notification_type.value,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat(),
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "related_entity_type": n.related_entity_type,
        "related_entity_id": n.related_entity_id,
    }


def _pagination_params():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(request.args.get("per_page", 20, type=int), MAX_PER_PAGE)
    return page, per_page


def _paginated_response(result):
    return jsonify({
        "notifications": [serialize_notification(n) for n in result.items],
        "total": result.total,
        "page": result.page,
        "pages": result.pages,
    }), 200


def _format_validation_errors(exc: ValidationError):
    return [
        {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]


@notification_bp.get("")
@jwt_required()
@role_required(Role.ADMIN, Role.TEACHER, Role.STUDENT)
def list_notifications():
    recipient_id = int(get_jwt_identity())
    page, per_page = _pagination_params()
    return _paginated_response(
        get_my_notifications(recipient_id, page, per_page)
    )


@notification_bp.get("/unread")
@jwt_required()
def list_unread_notifications():
    recipient_id = int(get_jwt_identity())
    page, per_page = _pagination_params()
    return _paginated_response(
        get_unread_notifications(recipient_id, page, per_page)
    )


@notification_bp.get("/<int:notification_id>")
@jwt_required()
def get_notification_route(notification_id):
    recipient_id = int(get_jwt_identity())
    notification = get_notification(notification_id, recipient_id)
    if notification is None:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify(serialize_notification(notification)), 200


@notification_bp.patch("/<int:notification_id>/read")
@jwt_required()
def mark_read(notification_id):
    recipient_id = int(get_jwt_identity())
    notification = mark_notification_as_read(notification_id, recipient_id)
    if notification is None:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify(serialize_notification(notification)), 200


@notification_bp.patch("/read-all")
@jwt_required()
def mark_all_read():
    recipient_id = int(get_jwt_identity())
    count = mark_all_notifications_as_read(recipient_id)
    return jsonify({"updated": count}), 200


@notification_bp.delete("/<int:notification_id>")
@jwt_required()
def delete_notification_route(notification_id):
    recipient_id = int(get_jwt_identity())
    deleted = delete_notification(notification_id, recipient_id)
    if not deleted:
        return jsonify({"error": "Notification not found"}), 404
    return "", 204


@notification_bp.post("")
@jwt_required()
@limiter.limit("20/minute")
@role_required(Role.ADMIN)
def create_notification_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    try:
        # Validate incoming data using Pydantic request schema
        validated_data = CreateNotificationRequest(**data)
        claims = get_jwt()
        actor = db.session.get(User, int(get_jwt_identity()))
        
        notification = create_notification(
            recipient_id=validated_data.recipient_id,
            title=validated_data.title,
            message=validated_data.message,
            notification_type=validated_data.notification_type,
            school_id=claims.get("school_id") or (actor.school_id if actor else None),
            related_entity_type=validated_data.related_entity_type,
            related_entity_id=validated_data.related_entity_id,
        )
        
        return jsonify(serialize_notification(notification)), 201

    except ValidationError as exc:
        return jsonify({"details": _format_validation_errors(exc)}), 422

    except InvalidRecipientError:
        return jsonify({"error": "Invalid recipient ID"}), 400