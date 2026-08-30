# App/models/association.py

from school_app.extensions import db

student_subjects = db.Table(
    "student_subject",
    db.Column(
        "school_id",
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "student_id",
        db.Integer,
        db.ForeignKey("students.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "subject_id",
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

teacher_subjects = db.Table(
    "teacher_subject",
    db.Column(
        "school_id",
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "teacher_id",
        db.Integer,
        db.ForeignKey("teachers.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "subject_id",
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

classroom_subjects = db.Table(
    "classroom_subject",
    db.Column(
        "school_id",
        db.Integer,
        db.ForeignKey("schools.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    db.Column(
        "classroom_id",
        db.Integer,
        db.ForeignKey("classrooms.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "subject_id",
        db.Integer,
        db.ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)