from collections import defaultdict
from sqlalchemy import select, func

from school_app.extensions import db
from school_app.models.result import Result
from school_app.models.exam import Exam
from school_app.models.subject import Subject
from school_app.models.classroom import Classroom
from school_app.models.student import Student
from school_app.modules.grading.services.grade_service import calculate_grade, GRADE_SCALE, normalize_score

PASS_THRESHOLD = 40  # interpreted as a percentage (0-100) — see FIX note below


def _filtered_results_query(session_id=None, classroom_id=None, subject_id=None):
    query = select(Result, Exam).join(Exam, Result.exam_id == Exam.id)
    if session_id is not None:
        query = query.where(Exam.session_id == session_id)
    if classroom_id is not None:
        query = query.where(Exam.classroom_id == classroom_id)
    if subject_id is not None:
        query = query.where(Exam.subject_id == subject_id)
    return query


def get_admin_report_academic(session_id=None, classroom_id=None, subject_id=None):
    rows = db.session.execute(
        _filtered_results_query(session_id, classroom_id, subject_id)
    ).all()

    grade_letters = [g for _, g in GRADE_SCALE]

    if not rows:
        return {
            "overall_average": None,
            "pass_rate": None,
            "fail_rate": None,
            "total_results": 0,
            "grade_distribution": {g: 0 for g in grade_letters},
            "subjects": [],
            "classrooms": [],
            "exams": [],
            "top_students": [],
            "lowest_students": [],
        }

    # FIX: every section below used to work directly off result.marks_obtained
    # (a raw score against that exam's own total_marks) and combined those
    # raw numbers across different exams — e.g. an 18/20 assignment and a
    # 70/100 final both being averaged as if "18" and "70" were on the same
    # scale. PASS_THRESHOLD=40 was then compared against those raw numbers
    # too, so it only worked out to something sensible by coincidence when
    # everything happened to be graded out of ~100. Normalizing every row to
    # a 0-100 percentage up front, once, fixes every section that follows —
    # they all now operate on comparable numbers.
    normalized_rows = [
        (result, exam, normalize_score(result.marks_obtained, exam.total_marks))
        for result, exam in rows
    ]

    all_percentages = [pct for _, _, pct in normalized_rows]
    overall_average = round(sum(all_percentages) / len(all_percentages), 2)
    pass_count = sum(1 for p in all_percentages if p >= PASS_THRESHOLD)
    fail_count = len(all_percentages) - pass_count
    pass_rate = round(pass_count / len(all_percentages) * 100, 1)
    fail_rate = round(100 - pass_rate, 1)

    grade_distribution = {g: 0 for g in grade_letters}
    for p in all_percentages:
        grade_distribution[calculate_grade(p)] += 1

    # ---- Subject performance ----
    by_subject = defaultdict(list)
    for result, exam, pct in normalized_rows:
        by_subject[exam.subject_id].append(pct)

    subject_names = {
        s.id: s.name for s in db.session.execute(
            select(Subject).where(Subject.id.in_(by_subject.keys()))
        ).scalars().all()
    } if by_subject else {}

    subjects_report = []
    for subject_id_key, percentages in by_subject.items():
        p = sum(1 for pct in percentages if pct >= PASS_THRESHOLD)
        subjects_report.append({
            "subject_id": subject_id_key,
            "subject_name": subject_names.get(subject_id_key, "Unknown"),
            "number_of_students": len(percentages),
            "average_percentage": round(sum(percentages) / len(percentages), 2),
            "highest_percentage": round(max(percentages), 2),
            "lowest_percentage": round(min(percentages), 2),
            "pass_count": p,
            "fail_count": len(percentages) - p,
        })
    subjects_report.sort(key=lambda s: s["subject_name"])

    # ---- Classroom performance (needs per-student average first) ----
    by_classroom_student = defaultdict(lambda: defaultdict(list))
    for result, exam, pct in normalized_rows:
        by_classroom_student[exam.classroom_id][result.student_id].append(pct)

    classroom_names = {
        c.id: c.name for c in db.session.execute(
            select(Classroom).where(Classroom.id.in_(by_classroom_student.keys()))
        ).scalars().all()
    } if by_classroom_student else {}

    classrooms_report = []
    for classroom_id_key, students_percentages in by_classroom_student.items():
        student_averages = [sum(p) / len(p) for p in students_percentages.values()]
        flat_percentages = [pct for percentages in students_percentages.values() for pct in percentages]
        p = sum(1 for pct in flat_percentages if pct >= PASS_THRESHOLD)
        classrooms_report.append({
            "classroom_id": classroom_id_key,
            "classroom_name": classroom_names.get(classroom_id_key, "Unknown"),
            "student_count": len(students_percentages),
            "average": round(sum(student_averages) / len(student_averages), 2),
            "highest_average": round(max(student_averages), 2),
            "lowest_average": round(min(student_averages), 2),
            "pass_rate": round(p / len(flat_percentages) * 100, 1),
            "fail_rate": round(100 - (p / len(flat_percentages) * 100), 1),
        })
    classrooms_report.sort(key=lambda c: c["classroom_name"])

    # ---- Exam performance ----
    # Left as raw marks_obtained deliberately — this groups by a single exam,
    # so every row already shares the same total_marks. Raw marks here are
    # not being compared against anything from a different scale, so this
    # section wasn't part of the bug.
    by_exam = defaultdict(list)
    exam_titles = {}
    for result, exam in rows:
        by_exam[exam.id].append(result.marks_obtained)
        exam_titles[exam.id] = exam.title

    exams_report = [
        {
            "exam_id": exam_id,
            "exam_title": exam_titles[exam_id],
            "number_of_students": len(marks),
            "average_mark": round(sum(marks) / len(marks), 2),
            "highest_mark": max(marks),
            "lowest_mark": min(marks),
        }
        for exam_id, marks in by_exam.items()
    ]
    exams_report.sort(key=lambda e: e["exam_title"])

    # ---- Top / lowest performing students ----
    by_student = defaultdict(list)
    for result, exam, pct in normalized_rows:
        by_student[result.student_id].append(pct)

    student_ids = list(by_student.keys())
    student_names = {
        s.id: s.full_name for s in db.session.execute(
            select(Student).where(Student.id.in_(student_ids))
        ).scalars().all()
    } if student_ids else {}

    student_averages = [
        {
            "student_id": sid,
            "student_name": student_names.get(sid, "Unknown"),
            "average": round(sum(percentages) / len(percentages), 2),
            "grade": calculate_grade(sum(percentages) / len(percentages)),
        }
        for sid, percentages in by_student.items()
    ]
    ranked = sorted(student_averages, key=lambda s: s["average"], reverse=True)

    return {
        "overall_average": overall_average,
        "pass_rate": pass_rate,
        "fail_rate": fail_rate,
        "total_results": len(all_percentages),
        "grade_distribution": grade_distribution,
        "subjects": subjects_report,
        "classrooms": classrooms_report,
        "exams": exams_report,
        "top_students": ranked[:5],
        "lowest_students": ranked[-5:][::-1],
    }