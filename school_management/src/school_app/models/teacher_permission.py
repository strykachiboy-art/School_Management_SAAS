# App/models/teacher_permission.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.permission import Permission


def _utcnow():
    return datetime.now(timezone.utc)


class TeacherPermission(db.Model):
    __tablename__ = "teacher_permissions"

    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "teacher_id", "permission",
            name="uq_teacher_permission_per_school",
        ), {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission = db.Column(db.Enum(Permission), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # Relationships
    school = db.relationship("School", backref=db.backref("teacher_permissions", lazy="dynamic"))
    teacher = db.relationship("Teacher", back_populates="permissions")