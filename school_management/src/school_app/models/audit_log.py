# App/models/audit_log.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.audit import AuditAction


def _utcnow():
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}
    
    id = db.Column(db.Integer, primary_key=True)

    # Tenant context (nullable to allow logging platform-level/super-admin actions)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    actor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action = db.Column(db.Enum(AuditAction), nullable=False)

    resource_type = db.Column(db.String(100), nullable=False)

    resource_id = db.Column(db.Integer, nullable=True)

    description = db.Column(db.Text, nullable=False)

    changes = db.Column(db.JSON, nullable=True)

    # Security metadata
    ip_address = db.Column(db.String(45), nullable=True)

    user_agent = db.Column(db.String(255), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        db.Index("idx_audit_school_resource", "school_id", "resource_type", "resource_id"),
        db.Index("idx_audit_school_created", "school_id", "created_at"),
    )

    # Unidirectional relationship (no back_populates on User to prevent loading massive log arrays in memory)
    school = db.relationship("School", foreign_keys=[school_id])
    actor = db.relationship("User", foreign_keys=[actor_id])

    def __repr__(self):
        return (
            f"<AuditLog id={self.id} "
            f"school_id={self.school_id} "
            f"action={self.action.value if hasattr(self.action, 'value') else self.action} "
            f"actor={self.actor_id}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "school_id": self.school_id,
            "actor_id": self.actor_id,
            "action": (
                self.action.value
                if hasattr(self.action, "value")
                else str(self.action)
            ),
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "description": self.description,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }