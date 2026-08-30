from collections import defaultdict
from sqlalchemy import select
from school_app.extensions import db
from school_app.models.teacher import Teacher
from school_app.models.classroom import Classroom
from school_app.models.subject import Subject
from school_app.models.timetable import Timetable


def get_admin_report_teachers(gender=None, subject_id=None, classroom_id=None, is_active=None):
    query = select(Teacher)
    if gender is not None:
        query = query.where(Teacher.gender == gender)
    if is_active is not None:
        query = query.where(Teacher.is_active == is_active)
    if subject_id is not None:
        query = query.join(Teacher.subjects).where(Subject.id == subject_id)
    if classroom_id is not None:
        query = query.join(Teacher.classrooms).where(Classroom.id == classroom_id)

    teachers = db.session.execute(query).scalars().unique().all()
    total_teachers = len(teachers)

    active_count = sum(1 for t in teachers if t.is_active)
    inactive_count = total_teachers - active_count

    by_gender = defaultdict(int)
    for t in teachers:
        by_gender[t.gender or "unspecified"] += 1

    # Timetable slot counts per teacher, in one query rather than N+1.
    teacher_ids = [t.id for t in teachers]
    timetable_rows = db.session.execute(
        select(Timetable.teacher_id, Timetable.id).where(Timetable.teacher_id.in_(teacher_ids))
    ).all() if teacher_ids else []
    slots_by_teacher = defaultdict(int)
    for tid, _ in timetable_rows:
        slots_by_teacher[tid] += 1

    teachers_report = []
    for t in teachers:
        homeroom_classrooms = [c.name for c in t.classrooms]
        student_count = sum(len(c.students) for c in t.classrooms)
        subject_names = [s.name for s in t.subjects]

        teachers_report.append({
            "teacher_id": t.id,
            "full_name": t.full_name,
            "email": t.email,
            "phone": t.phone,
            "gender": t.gender,
            "is_active": t.is_active,
            "subjects": subject_names,
            "homeroom_classrooms": homeroom_classrooms,
            "student_count": student_count,
            "weekly_timetable_slots": slots_by_teacher.get(t.id, 0),
        })

    teachers_report.sort(key=lambda t: t["full_name"])

    return {
        "total_teachers": total_teachers,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "by_gender": dict(by_gender),
        "teachers": teachers_report,
    }