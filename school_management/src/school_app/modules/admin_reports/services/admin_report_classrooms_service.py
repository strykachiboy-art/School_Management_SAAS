from sqlalchemy import select

from school_app.extensions import db
from school_app.models.classroom import Classroom
from school_app.models.teacher import Teacher
from school_app.models.timetable import Timetable
from school_app.models.subject import Subject
from school_app.modules.admin_reports.services.admin_report_academic_service import get_admin_report_academic
from school_app.modules.admin_reports.services.admin_report_attendance_service import get_admin_report_attendance


def get_admin_report_classrooms(session_id=None, term_id=None):
    classrooms = db.session.execute(select(Classroom)).scalars().all()

    academic = get_admin_report_academic(session_id=session_id)
    attendance = get_admin_report_attendance(session_id=session_id, term_id=term_id)

    academic_by_classroom = {c["classroom_id"]: c for c in academic["classrooms"]}
    attendance_by_classroom = {c["classroom_id"]: c for c in attendance["by_classroom"]}

    teacher_ids = {c.teacher_id for c in classrooms if c.teacher_id is not None}
    teacher_names = {
        t.id: t.full_name for t in db.session.execute(
            select(Teacher).where(Teacher.id.in_(teacher_ids))
        ).scalars().all()
    } if teacher_ids else {}

    # Subject teachers per classroom — homeroom teacher_id only covers
    # who's responsible for the class overall, not who's actually
    # teaching in it. Pulled from Timetable so a classroom with, say,
    # a Math teacher who isn't the homeroom teacher still shows up.
    classroom_ids = [c.id for c in classrooms]
    timetable_query = (
        select(Timetable.classroom_id, Timetable.teacher_id, Teacher.full_name,
               Timetable.subject_id, Subject.name)
        .join(Teacher, Timetable.teacher_id == Teacher.id)
        .join(Subject, Timetable.subject_id == Subject.id)
        .where(Timetable.classroom_id.in_(classroom_ids))
    )
    if term_id is not None:
        timetable_query = timetable_query.where(Timetable.term_id == term_id)

    subject_teachers_by_classroom = {}
    seen = set()
    for classroom_id, teacher_id, teacher_name, subject_id, subject_name in db.session.execute(timetable_query).all():
        key = (classroom_id, teacher_id, subject_id)
        if key in seen:
            continue
        seen.add(key)
        subject_teachers_by_classroom.setdefault(classroom_id, []).append({
            "teacher_id": teacher_id,
            "teacher_name": teacher_name,
            "subject_id": subject_id,
            "subject_name": subject_name,
        })

    report = []
    for classroom in classrooms:
        student_count = len(classroom.students)
        academic_stats = academic_by_classroom.get(classroom.id)
        attendance_stats = attendance_by_classroom.get(classroom.id)

        report.append({
            "classroom_id": classroom.id,
            "classroom_name": classroom.name,
            "capacity": classroom.capacity,
            "student_count": student_count,
            "capacity_utilization": (
                round(student_count / classroom.capacity * 100, 1)
                if classroom.capacity else None
            ),
            "homeroom_teacher_id": classroom.teacher_id,
            "homeroom_teacher_name": teacher_names.get(classroom.teacher_id) if classroom.teacher_id else None,
            "subject_teachers": subject_teachers_by_classroom.get(classroom.id, []),
            "academic_average": academic_stats["average"] if academic_stats else None,
            "academic_pass_rate": academic_stats["pass_rate"] if academic_stats else None,
            "attendance_rate": attendance_stats["attendance_rate"] if attendance_stats else None,
        })

    report.sort(key=lambda c: c["classroom_name"])
    return report