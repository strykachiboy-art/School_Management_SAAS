# App/models/timetable.py

from datetime import datetime, timezone
from school_app.extensions import db
from school_app.enums.day_of_week import DayOfWeek


def _utcnow():
    return datetime.now(timezone.utc)


class Timetable(db.Model):
    __tablename__ = "timetables"
    __table_args__ = (
        db.UniqueConstraint(
            "school_id", "classroom_id", "day_of_week", "start_time",
            name="uq_classroom_schedule_per_school",
        ),
        db.UniqueConstraint(
            "school_id", "teacher_id", "day_of_week", "start_time",
            name="uq_teacher_schedule_per_school",
        ), 
        {"extend_existing": True},
    )

    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term_id = db.Column(
        db.Integer,
        db.ForeignKey("terms.id", ondelete="CASCADE"),
        nullable=False,
    )
    classroom_id = db.Column(
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week = db.Column(db.Enum(DayOfWeek), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )

    # Relationships
    school = db.relationship("School", backref=db.backref("timetables", lazy="dynamic"))
    term = db.relationship("Term")
    classroom = db.relationship("Classroom")
    subject = db.relationship("Subject")
    teacher = db.relationship("Teacher")