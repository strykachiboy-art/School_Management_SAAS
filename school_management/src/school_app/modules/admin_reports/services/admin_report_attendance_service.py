from collections import defaultdict
from sqlalchemy import select, func

from school_app.extensions import db
from school_app.models.attendance import Attendance
from school_app.models.term import Term
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.enums.attendance import AttendanceStatus


def _filtered_query(session_id=None, term_id=None, classroom_id=None, student_id=None, start_date=None, end_date=None):
    query = select(Attendance).join(Term, Attendance.term_id == Term.id)
    needs_student_join = classroom_id is not None
    if needs_student_join:
        query = query.join(Student, Attendance.student_id == Student.id)

    if session_id is not None:
        query = query.where(Term.academic_session_id == session_id)
    if term_id is not None:
        query = query.where(Attendance.term_id == term_id)
    if classroom_id is not None:
        query = query.where(Student.classroom_id == classroom_id)
    if student_id is not None:
        query = query.where(Attendance.student_id == student_id)
    if start_date is not None:
        query = query.where(Attendance.date >= start_date)
    if end_date is not None:
        query = query.where(Attendance.date <= end_date)
    return query


def get_admin_report_attendance(
    session_id=None, 
    term_id=None, 
    classroom_id=None, 
    student_id=None, 
    start_date=None, 
    end_date=None,
    page=1,      
    page_size=10
):
    records = db.session.execute(
        _filtered_query(session_id, term_id, classroom_id, student_id, start_date, end_date)
    ).scalars().all()

    by_status = {status.value: 0 for status in AttendanceStatus}
    for r in records:
        by_status[r.status.value] += 1

    total = len(records)
    attendance_rate = (
        round(by_status[AttendanceStatus.PRESENT.value] / total * 100, 1)
        if total
        else None
    )

    student_ids = {r.student_id for r in records}
    students_by_id = {
        s.id: s for s in db.session.execute(
            select(Student).where(Student.id.in_(student_ids))
        ).scalars().all()
    } if student_ids else {}

    classroom_ids = {s.classroom_id for s in students_by_id.values() if s.classroom_id is not None}
    classroom_names = {
        c.id: c.name for c in db.session.execute(
            select(Classroom).where(Classroom.id.in_(classroom_ids))
        ).scalars().all()
    } if classroom_ids else {}

    by_classroom_records = defaultdict(list)
    for r in records:
        student = students_by_id.get(r.student_id)
        cid = student.classroom_id if student else None
        by_classroom_records[cid].append(r)

    classrooms_report = []
    for cid, recs in by_classroom_records.items():
        present = sum(1 for r in recs if r.status == AttendanceStatus.PRESENT)
        classrooms_report.append({
            "classroom_id": cid,
            "classroom_name": classroom_names.get(cid, "Unknown") if cid else "Unassigned",
            "total_records": len(recs),
            "attendance_rate": round(present / len(recs) * 100, 1) if recs else None,
        })
    classrooms_report.sort(key=lambda c: c["classroom_name"])

    # ---- By student ----
    by_student_records = defaultdict(list)
    for r in records:
        by_student_records[r.student_id].append(r)

    students_report = []
    for sid, recs in by_student_records.items():
        present = sum(1 for r in recs if r.status == AttendanceStatus.PRESENT)
        student = students_by_id.get(sid)
        students_report.append({
            "student_id": sid,
            "student_name": student.full_name if student else "Unknown",
            "total_records": len(recs),
            "attendance_rate": round(present / len(recs) * 100, 1) if recs else None,
        })
    students_report.sort(key=lambda s: s["student_name"])

    # ---- Trend: attendance rate per calendar date ----
    by_date_records = defaultdict(list)
    for r in records:
        by_date_records[r.date].append(r)

    trend = []
    for d in sorted(by_date_records.keys()):
        recs = by_date_records[d]
        present = sum(1 for r in recs if r.status == AttendanceStatus.PRESENT)
        trend.append({
            "date": d.isoformat(),
            "total_records": len(recs),
            "attendance_rate": round(present / len(recs) * 100, 1) if recs else None,
        })

    return {
        "total_records": total,
        "by_status": by_status,
        "attendance_rate": attendance_rate,
        "by_classroom": classrooms_report,
        "by_student": students_report,
        "trend": trend,
    }