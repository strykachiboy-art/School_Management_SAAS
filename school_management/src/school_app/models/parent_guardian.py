# App/models/parent_guardian.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.parent_guardian import ParentGuardianEnum


def _utcnow():
    return datetime.now(timezone.utc)


class ParentGuardian(db.Model):
    __tablename__ = "parentguardians"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(50), nullable=True)
    occupation = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("parent_guardians", lazy="dynamic"))
    user = db.relationship("User")


class ParentGuardianStudent(db.Model):
    __tablename__ = "parent_guardian_students"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "parent_guardian_id", "student_id",
            name="uq_parent_student_per_school",
        ), {"extend_existing": True}
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_guardian_id = db.Column(db.Integer, db.ForeignKey("parentguardians.id", ondelete="CASCADE"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    relationship = db.Column(db.Enum(ParentGuardianEnum), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    school = db.relationship("School", backref=db.backref("parent_guardian_students", lazy="dynamic"))
    parent_guardian = db.relationship("ParentGuardian", backref=db.backref("student_associations", cascade="all, delete-orphan"))
    student = db.relationship("Student", backref=db.backref("parent_associations", cascade="all, delete-orphan"))