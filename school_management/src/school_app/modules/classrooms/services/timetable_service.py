from flask import abort
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from school_app.extensions import db
from school_app.models.timetable import Timetable
from school_app.models.subject import Subject
from school_app.models.classroom import Classroom
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction


# ========================= Helper: Overlap Check ========================

def _check_schedule_conflict(term_id, day_of_week, start_time, end_time, teacher_id=None, classroom_id=None, exclude_id=None):
    if start_time >= end_time:
        abort(400, description="start_time must be earlier than end_time.")

    stmt = db.select(Timetable).where(
        Timetable.term_id == term_id,
        Timetable.day_of_week == day_of_week,
        Timetable.start_time < end_time,
        Timetable.end_time > start_time,
    )

    if exclude_id:
        stmt = stmt.where(Timetable.id != exclude_id)

    conflict_conditions = []
    if teacher_id:
        conflict_conditions.append(Timetable.teacher_id == teacher_id)
    if classroom_id:
        conflict_conditions.append(Timetable.classroom_id == classroom_id)

    if conflict_conditions:
        stmt = stmt.where(or_(*conflict_conditions))
        existing = db.session.scalars(stmt).first()
        if existing:
            if existing.teacher_id == teacher_id:
                abort(409, description="Teacher is already scheduled for another class during this time slot.")
            if existing.classroom_id == classroom_id:
                abort(409, description="Classroom is already occupied during this time slot.")


# ========================= Create Timetable ========================

def create_timetable(data, actor_id=None):
    _check_schedule_conflict(
        term_id=data["term_id"],
        day_of_week=data["day_of_week"],
        start_time=data["start_time"],
        end_time=data["end_time"],
        teacher_id=data["teacher_id"],
        classroom_id=data["classroom_id"],
    )

    timetable = Timetable(
        term_id=data["term_id"],
        classroom_id=data["classroom_id"],
        subject_id=data["subject_id"],
        teacher_id=data["teacher_id"],
        day_of_week=data["day_of_week"],
        start_time=data["start_time"],
        end_time=data["end_time"],
    )
    db.session.add(timetable)
    
    try:
        db.session.flush()  # Forces SQL execution to catch constraints and populate timetable.id
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not create timetable — check foreign key constraints.")
    
    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.CREATE,
            resource_type="Timetable",
            resource_id=timetable.id,
            description=f"Created timetable entry ID {timetable.id} for classroom ID {timetable.classroom_id}",
        )
        
    db.session.commit()

    return timetable


# ========================= Get Single Timetable ========================

def get_timetable(timetable_id):
    timetable = db.session.get(Timetable, timetable_id)
    if not timetable:
        abort(404, description=f"Timetable entry with ID {timetable_id} not found.")
    return timetable


# ========================= Get Timetables =========================

def get_timetables(search="", term_id=None, classroom_id=None, teacher_id=None, day_of_week=None, page=1, per_page=10):
    stmt = db.select(Timetable)

    if term_id:
        stmt = stmt.where(Timetable.term_id == term_id)
    if classroom_id:
        stmt = stmt.where(Timetable.classroom_id == classroom_id)
    if teacher_id:
        stmt = stmt.where(Timetable.teacher_id == teacher_id)
    if day_of_week:
        stmt = stmt.where(Timetable.day_of_week == day_of_week)

    if search:
        stmt = (
            stmt.join(Timetable.subject)
            .join(Timetable.classroom)
            .where(
                or_(
                    Subject.name.ilike(f"%{search}%"),
                    Classroom.name.ilike(f"%{search}%"),
                )
            )
        )

    stmt = stmt.order_by(Timetable.day_of_week.asc(), Timetable.start_time.asc())
    return db.paginate(stmt, page=page, per_page=per_page, error_out=False)


# ========================= Update Timetable =========================

def update_timetable(timetable_id, data, actor_id=None):
    timetable = get_timetable(timetable_id)

    old_values = {
        "term_id": timetable.term_id,
        "classroom_id": timetable.classroom_id,
        "subject_id": timetable.subject_id,
        "teacher_id": timetable.teacher_id,
        "day_of_week": timetable.day_of_week,
        "start_time": timetable.start_time,
        "end_time": timetable.end_time,
    }

    term_id = getattr(data, "term_id", timetable.term_id)
    classroom_id = getattr(data, "classroom_id", timetable.classroom_id)
    subject_id = getattr(data, "subject_id", timetable.subject_id)
    teacher_id = getattr(data, "teacher_id", timetable.teacher_id)
    day_of_week = getattr(data, "day_of_week", timetable.day_of_week)
    start_time = getattr(data, "start_time", timetable.start_time)
    end_time = getattr(data, "end_time", timetable.end_time)

    _check_schedule_conflict(
        term_id=term_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        teacher_id=teacher_id,
        classroom_id=classroom_id,
        exclude_id=timetable_id,
    )

    new_values = {
        "term_id": term_id,
        "classroom_id": classroom_id,
        "subject_id": subject_id,
        "teacher_id": teacher_id,
        "day_of_week": day_of_week,
        "start_time": start_time,
        "end_time": end_time,
    }

    changes = {}
    for key, new_val in new_values.items():
        old_val = old_values[key]
        if new_val is not None and new_val != old_val:
            changes[key] = {"before": str(old_val), "after": str(new_val)}

    timetable.term_id = term_id
    timetable.classroom_id = classroom_id
    timetable.subject_id = subject_id
    timetable.teacher_id = teacher_id
    timetable.day_of_week = day_of_week
    timetable.start_time = start_time
    timetable.end_time = end_time

    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        abort(400, description="Could not update timetable — check foreign key constraints.")

    if changes and actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.UPDATE,
            resource_type="Timetable",
            resource_id=timetable.id,
            description=f"Updated timetable entry ID {timetable.id}",
            changes=changes,
        )
        
    db.session.commit()

    return timetable


# ========================= Delete Timetable =========================

def delete_timetable(timetable_id, actor_id=None):
    timetable = get_timetable(timetable_id)
    classroom_id = timetable.classroom_id
    
    db.session.delete(timetable)

    if actor_id:
        create_audit_log(
            actor_id=actor_id,
            action=AuditAction.DELETE,
            resource_type="Timetable",
            resource_id=timetable_id,
            description=f"Deleted timetable entry ID {timetable_id} for classroom ID {classroom_id}",
        )
        
    db.session.commit()

    return True


# ========================= Get Teacher Timetable =========================

def get_teacher_timetable(teacher_id, term_id=None, day_of_week=None):
    stmt = db.select(Timetable).where(Timetable.teacher_id == teacher_id)

    if term_id:
        stmt = stmt.where(Timetable.term_id == term_id)
    if day_of_week:
        stmt = stmt.where(Timetable.day_of_week == day_of_week)

    stmt = stmt.order_by(Timetable.day_of_week.asc(), Timetable.start_time.asc())
    return db.session.scalars(stmt).all()


# ========================= Get Classroom Timetable =========================

def get_classroom_timetable(classroom_id, term_id=None, day_of_week=None):
    stmt = db.select(Timetable).where(Timetable.classroom_id == classroom_id)

    if term_id:
        stmt = stmt.where(Timetable.term_id == term_id)
    if day_of_week:
        stmt = stmt.where(Timetable.day_of_week == day_of_week)

    stmt = stmt.order_by(Timetable.day_of_week.asc(), Timetable.start_time.asc())
    return db.session.scalars(stmt).all()