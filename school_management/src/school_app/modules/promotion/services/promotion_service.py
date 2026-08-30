from school_app.extensions import db
from school_app.models.student import Student
from school_app.models.classroom import Classroom
from school_app.models.academic_session import AcademicSession
from school_app.models.academic_level import AcademicLevel
from school_app.models.section import Section
from school_app.models.exam import Exam
from school_app.models.result import Result
from school_app.models.attendance import Attendance
from school_app.models.term import Term
from school_app.models.promotion_history import PromotionHistory
from school_app.models.promotion_rule import PromotionRule
from school_app.enums.promotion import PromotionDecision
from school_app.enums.attendance import AttendanceStatus
from school_app.modules.audit.services.audit_log_service import create_audit_log
from school_app.enums.audit import AuditAction
from school_app.modules.grading.services.grade_service import calculate_overall_average, get_subject_scores
from school_app.modules.promotion.services.promotion_rule_service import get_active_rule_for_level
from school_app.modules.people.services.enrollment_service import record_enrollment
from school_app.enums.enrollment import EnrollmentStatus

PASS_AVERAGE_THRESHOLD = 50.0
MIN_ATTENDANCE_THRESHOLD = 75.0


def _get_current_level(classroom):
    if classroom is None or classroom.section_id is None:
        return None
    return classroom.section.level if classroom.section else None


def _count_failed_subjects(student_id, academic_session_id, min_subject_score, school_id):
    stmt = (
        db.select(Result)
        .join(Exam, Result.exam_id == Exam.id)
        .where(
            Result.student_id == student_id,
            Exam.session_id == academic_session_id,
            Result.school_id == school_id
        )
    )
    results = db.session.scalars(stmt).all()

    if not results:
        return 0

    subject_scores = get_subject_scores(results)
    return sum(1 for score in subject_scores.values() if score < min_subject_score)


def _find_classroom_for_level(current_classroom, target_level_id, school_id):
    stmt = (
        db.select(Classroom)
        .join(Section, Classroom.section_id == Section.id)
        .where(
            Section.level_id == target_level_id,
            Classroom.school_id == school_id
        )
    )

    current_section_name = None
    if current_classroom is not None and current_classroom.section_id is not None and current_classroom.section:
        current_section_name = current_classroom.section.name

    if current_section_name is not None:
        matching_stmt = stmt.where(Section.name == current_section_name)
        match = db.session.scalars(matching_stmt).first()
        if match is not None:
            return match

    return db.session.scalars(stmt).first()


def _calculate_average_score(student_id, academic_session_id, school_id):
    stmt = (
        db.select(Result)
        .join(Exam, Result.exam_id == Exam.id)
        .where(
            Result.student_id == student_id,
            Exam.session_id == academic_session_id,
            Result.school_id == school_id
        )
    )
    results = db.session.scalars(stmt).all()

    if not results:
        return 0.0

    return round(calculate_overall_average(results), 2)


def _calculate_attendance_percentage(student_id, academic_session_id, school_id):
    stmt = (
        db.select(Attendance.status)
        .join(Term, Attendance.term_id == Term.id)
        .where(
            Attendance.student_id == student_id,
            Term.academic_session_id == academic_session_id,
            Attendance.school_id == school_id
        )
    )
    statuses = db.session.scalars(stmt).all()

    if not statuses:
        return 0.0

    excused_count = sum(1 for s in statuses if s == AttendanceStatus.EXCUSED)
    effective_total = len(statuses) - excused_count

    if effective_total <= 0:
        return 100.0

    present_equivalent = sum(
        1 for s in statuses if s in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
    )

    return round((present_equivalent / effective_total) * 100, 2)


def evaluate_student_promotion(student_id, academic_session_id, school_id):
    student = db.session.get(Student, student_id)
    if student is None or student.school_id != school_id:
        return None

    session = db.session.get(AcademicSession, academic_session_id)
    if session is None or session.school_id != school_id:
        return None

    average_score = _calculate_average_score(student_id, academic_session_id, school_id)
    attendance_percentage = _calculate_attendance_percentage(student_id, academic_session_id, school_id)

    current_classroom = (
        db.session.get(Classroom, student.classroom_id) if student.classroom_id else None
    )
    current_level = _get_current_level(current_classroom)
    # Assuming get_active_rule_for_level handles its own school filtering, or rule belongs to the level
    rule = get_active_rule_for_level(current_level.id) if current_level is not None else None

    if rule is not None:
        checks_passed = True

        if rule.min_average_score is not None and average_score < rule.min_average_score:
            checks_passed = False
        if rule.min_attendance_percentage is not None and attendance_percentage < rule.min_attendance_percentage:
            checks_passed = False
        if rule.max_failed_subjects is not None and rule.min_subject_score is not None:
            failed_subjects = _count_failed_subjects(student_id, academic_session_id, rule.min_subject_score, school_id)
            if failed_subjects > rule.max_failed_subjects:
                checks_passed = False

        if not checks_passed:
            recommendation = PromotionDecision.REPEATED
            target_level_id = None
        elif rule.to_level_id is None:
            recommendation = PromotionDecision.GRADUATED
            target_level_id = None
        else:
            recommendation = PromotionDecision.PROMOTED
            target_level_id = rule.to_level_id

        return {
            "student_id": student_id,
            "academic_session_id": academic_session_id,
            "average_score": average_score,
            "attendance_percentage": attendance_percentage,
            "recommendation": recommendation,
            "requires_admin_approval": rule.requires_admin_approval,
            "target_level_id": target_level_id,
        }

    passed = (
        average_score >= PASS_AVERAGE_THRESHOLD
        and attendance_percentage >= MIN_ATTENDANCE_THRESHOLD
    )

    if not passed:
        recommendation = PromotionDecision.REPEATED
    elif current_classroom is not None and getattr(current_classroom, "is_final_level", False):
        recommendation = PromotionDecision.GRADUATED
    else:
        recommendation = PromotionDecision.PROMOTED

    return {
        "student_id": student_id,
        "academic_session_id": academic_session_id,
        "average_score": average_score,
        "attendance_percentage": attendance_percentage,
        "recommendation": recommendation,
        "requires_admin_approval": False,
        "target_level_id": None,
    }


def promote_student(
    student_id,
    academic_session_id,
    to_classroom_id,
    school_id,
    remarks=None,
    decided_by=None,
    decided_by_role=None,
    allow_level_skip=False,
    actor_id=None,
):
    student = db.session.get(Student, student_id)
    if student is None or student.school_id != school_id:
        return None

    to_classroom = db.session.get(Classroom, to_classroom_id)
    if to_classroom is None or to_classroom.school_id != school_id:
        raise ValueError("Target classroom not found")

    from_classroom = (
        db.session.get(Classroom, student.classroom_id) if student.classroom_id else None
    )

    from_level = _get_current_level(from_classroom)
    to_level = _get_current_level(to_classroom)

    rule = get_active_rule_for_level(from_level.id) if from_level is not None else None

    if rule is not None:
        expected_to_level_id = rule.to_level_id
        actual_to_level_id = to_level.id if to_level is not None else None
        if expected_to_level_id != actual_to_level_id and not allow_level_skip:
            expected_name = rule.to_level.name if rule.to_level else "graduation (no further level)"
            actual_name = to_level.name if to_level is not None else "an unrecognized/unleveled classroom"
            raise ValueError(
                f"Cannot promote from level {from_level.name} to {actual_name}: "
                f"the active promotion rule expects {expected_name}. "
                "Pass allow_level_skip=true to override intentionally."
            )
    else:
        from_level_int = getattr(from_classroom, "level", None)
        to_level_int = getattr(to_classroom, "level", None)

        if from_classroom is not None and from_level_int is not None and to_level_int is not None:
            expected_level = from_level_int + 1
            if to_level_int != expected_level and not allow_level_skip:
                raise ValueError(
                    f"Cannot promote from level {from_level_int} to level "
                    f"{to_level_int}: expected level {expected_level}. "
                    "Pass allow_level_skip=true to override intentionally."
                )
        elif from_classroom is None and to_level_int is not None and to_level_int > 1 and not allow_level_skip:
            raise ValueError(
                f"Cannot assign unassigned student directly to level {to_level_int}. "
                "Pass allow_level_skip=true to override intentionally."
            )

    evaluation = evaluate_student_promotion(student_id, academic_session_id, school_id)

    if evaluation and evaluation["recommendation"] == PromotionDecision.REPEATED:
        if decided_by_role not in ("teacher", "admin"):
            raise PermissionError(
                "This student did not meet the promotion criteria — "
                "only a teacher or admin can decide to promote them anyway."
            )

    from_classroom_id = student.classroom_id
    record_enrollment(student_id, to_classroom_id, academic_session_id=academic_session_id, status=EnrollmentStatus.PROMOTED, recorded_by=actor_id, school_id=school_id)
    student.classroom_id = to_classroom_id

    final_remarks = remarks
    if allow_level_skip and to_level is not None:
        from_lvl = from_level if from_level is not None else "Unassigned"
        skip_note = f"[Level skip override: {from_lvl} -> {to_level}]"
        final_remarks = f"{skip_note} {remarks}" if remarks else skip_note

    history = PromotionHistory(
        school_id=school_id,
        student_id=student_id,
        academic_session_id=academic_session_id,
        from_classroom_id=from_classroom_id,
        to_classroom_id=to_classroom_id,
        decision=PromotionDecision.PROMOTED,
        average_score=evaluation["average_score"] if evaluation else None,
        attendance_percentage=evaluation["attendance_percentage"] if evaluation else None,
        remarks=final_remarks,
        decided_by=decided_by,
    )

    db.session.add(history)
    db.session.flush()

    effective_actor_id = actor_id if actor_id is not None else decided_by
    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.CREATE,
            resource_type="PromotionHistory",
            resource_id=history.id,
            description=f"Promoted student ID {student_id} to classroom ID {to_classroom_id}",
        )
        
    db.session.commit()

    return history


def repeat_student(student_id, academic_session_id, school_id, remarks=None, decided_by=None, actor_id=None):
    student = db.session.get(Student, student_id)
    if student is None or student.school_id != school_id:
        return None

    evaluation = evaluate_student_promotion(student_id, academic_session_id, school_id)

    history = PromotionHistory(
        school_id=school_id,
        student_id=student_id,
        academic_session_id=academic_session_id,
        from_classroom_id=student.classroom_id,
        to_classroom_id=student.classroom_id,
        decision=PromotionDecision.REPEATED,
        average_score=evaluation["average_score"] if evaluation else None,
        attendance_percentage=evaluation["attendance_percentage"] if evaluation else None,
        remarks=remarks,
        decided_by=decided_by,
    )

    db.session.add(history)
    db.session.flush()

    effective_actor_id = actor_id if actor_id is not None else decided_by
    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.CREATE,
            resource_type="PromotionHistory",
            resource_id=history.id,
            description=f"Recorded repeat status for student ID {student_id} in session ID {academic_session_id}",
        )
        
    db.session.commit()

    return history


def graduate_student(student_id, academic_session_id, school_id, remarks=None, decided_by=None, actor_id=None):
    student = db.session.get(Student, student_id)
    if student is None or student.school_id != school_id:
        return None

    evaluation = evaluate_student_promotion(student_id, academic_session_id, school_id)
    from_classroom_id = student.classroom_id

    record_enrollment(student_id, None, academic_session_id=academic_session_id, status=EnrollmentStatus.GRADUATED, recorded_by=actor_id, school_id=school_id)
    student.classroom_id = None

    history = PromotionHistory(
        school_id=school_id,
        student_id=student_id,
        academic_session_id=academic_session_id,
        from_classroom_id=from_classroom_id,
        to_classroom_id=None,
        decision=PromotionDecision.GRADUATED,
        average_score=evaluation["average_score"] if evaluation else None,
        attendance_percentage=evaluation["attendance_percentage"] if evaluation else None,
        remarks=remarks,
        decided_by=decided_by,
    )

    db.session.add(history)
    db.session.flush()

    effective_actor_id = actor_id if actor_id is not None else decided_by
    if effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.CREATE,
            resource_type="PromotionHistory",
            resource_id=history.id,
            description=f"Graduated student ID {student_id}",
        )
        
    db.session.commit()

    return history


def get_student_promotion_history(student_id, school_id, page=1, per_page=20):
    student = db.session.get(Student, student_id)
    if student is None or student.school_id != school_id:
        return None

    stmt = (
        db.select(PromotionHistory)
        .where(
            PromotionHistory.student_id == student_id,
            PromotionHistory.school_id == school_id
        )
        .order_by(PromotionHistory.created_at.asc())
    )

    total = db.session.scalar(
        db.select(db.func.count()).select_from(stmt.subquery())
    )

    paginated_stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    items = db.session.scalars(paginated_stmt).all()

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page if total else 0,
    }


def get_session_promotions(academic_session_id, school_id, decision=None, classroom_id=None):
    session = db.session.get(AcademicSession, academic_session_id)
    if session is None or session.school_id != school_id:
        return None

    stmt = (
        db.select(PromotionHistory)
        .where(
            PromotionHistory.academic_session_id == academic_session_id,
            PromotionHistory.school_id == school_id
        )
    )

    if decision is not None:
        stmt = stmt.where(PromotionHistory.decision == decision)

    if classroom_id is not None:
        stmt = stmt.where(
            db.or_(
                PromotionHistory.from_classroom_id == classroom_id,
                PromotionHistory.to_classroom_id == classroom_id,
            )
        )

    stmt = stmt.order_by(PromotionHistory.created_at.asc())
    return db.session.scalars(stmt).all()


def _find_next_classroom(current_classroom, school_id):
    if current_classroom is None or getattr(current_classroom, "level", None) is None:
        return None

    target_level = current_classroom.level + 1
    stmt = db.select(Classroom).where(
        Classroom.level == target_level,
        Classroom.school_id == school_id
    )

    if hasattr(current_classroom, "section") and current_classroom.section:
        stmt = stmt.where(Classroom.section == current_classroom.section)

    return db.session.scalars(stmt).first()


def promote_session_students(academic_session_id, school_id, classroom_id=None, decided_by=None, actor_id=None):
    session = db.session.get(AcademicSession, academic_session_id)
    if session is None or session.school_id != school_id:
        raise ValueError("Academic session not found")

    query = db.select(Student).where(
        Student.classroom_id.isnot(None),
        Student.school_id == school_id
    )
    
    if classroom_id is not None:
        query = query.where(Student.classroom_id == classroom_id)

    students = db.session.scalars(query).all()

    results = {"promoted": [], "repeated": [], "graduated": [], "skipped": []}
    history_records = []

    for student in students:
        evaluation = evaluate_student_promotion(student.id, academic_session_id, school_id)
        if evaluation is None:
            results["skipped"].append({"student_id": student.id, "reason": "evaluation unavailable"})
            continue

        current_classroom = (
            db.session.get(Classroom, student.classroom_id) if student.classroom_id else None
        )
        decision = evaluation["recommendation"]
        from_classroom_id = student.classroom_id

        if decision == PromotionDecision.REPEATED:
            to_classroom_id = student.classroom_id
            results["repeated"].append(student.id)

        elif decision == PromotionDecision.GRADUATED:
            to_classroom_id = None
            record_enrollment(student.id, None, academic_session_id=academic_session_id, status=EnrollmentStatus.GRADUATED, recorded_by=actor_id, school_id=school_id)
            student.classroom_id = None
            results["graduated"].append(student.id)

        elif decision == PromotionDecision.PROMOTED:
            target_level_id = evaluation.get("target_level_id")
            if target_level_id is not None:
                next_classroom = _find_classroom_for_level(current_classroom, target_level_id, school_id)
            else:
                next_classroom = _find_next_classroom(current_classroom, school_id)

            if next_classroom is None:
                results["skipped"].append(
                    {"student_id": student.id, "reason": "no next-level classroom configured"}
                )
                continue
            to_classroom_id = next_classroom.id
            record_enrollment(student.id, next_classroom.id, academic_session_id=academic_session_id, status=EnrollmentStatus.PROMOTED, recorded_by=actor_id, school_id=school_id)
            student.classroom_id = next_classroom.id
            results["promoted"].append(student.id)

        else:
            results["skipped"].append({"student_id": student.id, "reason": f"unhandled decision {decision}"})
            continue

        history_records.append(
            PromotionHistory(
                school_id=school_id,
                student_id=student.id,
                academic_session_id=academic_session_id,
                from_classroom_id=from_classroom_id,
                to_classroom_id=to_classroom_id,
                decision=decision,
                average_score=evaluation["average_score"],
                attendance_percentage=evaluation["attendance_percentage"],
                remarks="Bulk end-of-term promotion run",
                decided_by=decided_by,
            )
        )

    if history_records:
        db.session.add_all(history_records)
        
    db.session.flush()

    effective_actor_id = actor_id if actor_id is not None else decided_by
    if history_records and effective_actor_id:
        create_audit_log(
            actor_id=effective_actor_id,
            action=AuditAction.BULK_ACTION,
            resource_type="PromotionHistory",
            resource_id=None,
            description=f"Bulk processed end-of-term promotion run for session ID {academic_session_id}",
            changes={
                "promoted_count": len(results["promoted"]),
                "repeated_count": len(results["repeated"]),
                "graduated_count": len(results["graduated"]),
                "skipped_count": len(results["skipped"])
            }
        )
        
    db.session.commit()

    return results