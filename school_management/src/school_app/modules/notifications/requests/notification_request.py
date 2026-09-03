from pydantic import BaseModel, Field, field_validator
from school_app.enums.notification import NotificationType


class CreateNotificationRequest(BaseModel):
    recipient_id: int
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    notification_type: NotificationType
    related_entity_type: str | None = None
    related_entity_id: int | None = None

    @field_validator("title", "message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be blank")
        return v


class MarkNotificationReadRequest(BaseModel):
    # single mark-as-read takes id from the URL, so this is unused for now.
    # kept as a placeholder for a future bulk-read-by-ids endpoint.
    notification_ids: list[int] | None = None