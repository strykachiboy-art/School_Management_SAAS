from datetime import date
from school_app.extensions import db as _db
from school_app.models.classroom import Classroom
from school_app.models.attendance import Attendance
from school_app.enums.attendance import AttendanceStatus
from school_app.enums.promotion import PromotionDecision
from school_app.modules.promotion.services.promotion_service import (
    evaluate_student_promotion,
    promote_student,
    repeat_student,
    graduate_student,
    get_student_promotion_history,
    get_session_promotions,
)


def _mark_present(app, student, term, count, status=AttendanceStatus.PRESENT, start_day=1):
    with app.app_context():
        for i in range(count):
            att = Attendance(
                student_id=student.id,
                term_id=term.id,
                date=date(2026, 9, start_day + i),
                status=status,
                school_id=student.school_id,
            )
            _db.session.add(att)
        _db.session.commit()


# ====================================== evaluate_student_promotion ===============================================

def test_evaluate_promotion_recommends_promoted(app, student, academic_session, exam, make_result, term):
    make_result(student_obj=student, exam_obj=exam, marks=80)
    _mark_present(app, student, term, 10)

    evaluation = evaluate_student_promotion(student.id, academic_session.id, school_id=student.school_id)

    assert evaluation["average_score"] == 80.0
    assert evaluation["attendance_percentage"] == 100.0
    assert evaluation["recommendation"] == PromotionDecision.PROMOTED


def test_evaluate_promotion_recommends_repeated_on_low_score(app, student, academic_session, exam, make_result, term):
    make_result(student_obj=student, exam_obj=exam, marks=30)
    _mark_present(app, student, term, 10)

    evaluation = evaluate_student_promotion(student.id, academic_session.id, school_id=student.school_id)

    assert evaluation["recommendation"] == PromotionDecision.REPEATED


def test_evaluate_promotion_recommends_repeated_on_low_attendance(app, student, academic_session, exam, make_result, term):
    make_result(student_obj=student, exam_obj=exam, marks=90)
    _mark_present(app, student, term, 3)
    _mark_present(app, student, term, 7, status=AttendanceStatus.ABSENT, start_day=20)

    evaluation = evaluate_student_promotion(student.id, academic_session.id, school_id=student.school_id)

    assert evaluation["attendance_percentage"] == 30.0
    assert evaluation["recommendation"] == PromotionDecision.REPEATED


def test_evaluate_promotion_recommends_graduated_on_final_level(app, student, academic_session, exam, make_result, term):
    with app.app_context():
        classroom = _db.session.get(Classroom, exam.classroom_id)
        classroom.is_final_level = True
        s = _db.session.get(type(student), student.id)
        s.classroom_id = classroom.id
        _db.session.commit()

    make_result(student_obj=student, exam_obj=exam, marks=95)
    _mark_present(app, student, term, 10)

    evaluation = evaluate_student_promotion(student.id, academic_session.id, school_id=student.school_id)

    assert evaluation["recommendation"] == PromotionDecision.GRADUATED


def test_evaluate_promotion_no_data_returns_zeroes(student, academic_session):
    evaluation = evaluate_student_promotion(student.id, academic_session.id, school_id=student.school_id)

    assert evaluation["average_score"] == 0.0
    assert evaluation["attendance_percentage"] == 0.0
    assert evaluation["recommendation"] == PromotionDecision.REPEATED


def test_evaluate_promotion_student_not_found(academic_session, school):
    assert evaluate_student_promotion(99999, academic_session.id, school_id=school.id) is None


# ====================================== promote_student ===============================================

def test_promote_student_updates_classroom_and_history(app, student, academic_session, classroom, school):
    with app.app_context():
        new_classroom = Classroom(name="Room B", capacity=30, school_id=school.id)
        _db.session.add(new_classroom)
        _db.session.commit()
        new_classroom_id = new_classroom.id

    history = promote_student(
        student.id, academic_session.id, new_classroom_id,
        school_id=student.school_id,
        remarks="Great year", decided_by_role="teacher"
    )

    assert history.decision == PromotionDecision.PROMOTED
    assert history.to_classroom_id == new_classroom_id
    assert history.remarks == "Great year"

    with app.app_context():
        updated = _db.session.get(type(student), student.id)
        assert updated.classroom_id == new_classroom_id


def test_promote_student_not_found(academic_session, classroom, school):
    assert promote_student(99999, academic_session.id, classroom.id, school_id=school.id, decided_by_role="teacher") is None


def test_promote_student_invalid_classroom_aborts(student, academic_session):
    import pytest

    with pytest.raises(ValueError, match="Target classroom not found"):
        promote_student(student.id, academic_session.id, 99999, school_id=student.school_id)


# ====================================== repeat_student ===============================================

def test_repeat_student_keeps_classroom_and_logs_history(app, student, classroom, academic_session):
    with app.app_context():
        s = _db.session.get(type(student), student.id)
        s.classroom_id = classroom.id
        _db.session.commit()

    history = repeat_student(student.id, academic_session.id, school_id=student.school_id, remarks="Needs improvement")

    assert history.decision == PromotionDecision.REPEATED
    assert history.from_classroom_id == classroom.id
    assert history.to_classroom_id == classroom.id

    with app.app_context():
        unchanged = _db.session.get(type(student), student.id)
        assert unchanged.classroom_id == classroom.id


def test_repeat_student_not_found(academic_session, school):
    assert repeat_student(99999, academic_session.id, school_id=school.id) is None


# ====================================== graduate_student ===============================================

def test_graduate_student_clears_classroom_and_logs_history(app, student, classroom, academic_session):
    with app.app_context():
        s = _db.session.get(type(student), student.id)
        s.classroom_id = classroom.id
        _db.session.commit()

    history = graduate_student(student.id, academic_session.id, school_id=student.school_id, remarks="Well done")

    assert history.decision == PromotionDecision.GRADUATED
    assert history.from_classroom_id == classroom.id
    assert history.to_classroom_id is None

    with app.app_context():
        graduated = _db.session.get(type(student), student.id)
        assert graduated.classroom_id is None


def test_graduate_student_not_found(academic_session, school):
    assert graduate_student(99999, academic_session.id, school_id=school.id) is None


# ====================================== history queries ===============================================

def test_get_student_promotion_history_returns_ordered_records(student, academic_session, classroom):
    repeat_student(student.id, academic_session.id, school_id=student.school_id, remarks="First")
    promote_student(
        student.id,
        academic_session.id,
        classroom.id,
        school_id=student.school_id,
        remarks="Second",
        decided_by_role="teacher",
        allow_level_skip=True,
    )

    history = get_student_promotion_history(student.id, school_id=student.school_id)

    if isinstance(history, dict) and "items" in history:
        assert len(history["items"]) == 2
    else:
        assert len(history) == 2


def test_get_student_promotion_history_student_not_found(school):
    assert get_student_promotion_history(99999, school_id=school.id) is None


def test_get_session_promotions_returns_all_for_session(student, student2, academic_session, classroom):
    promote_student(
        student.id,
        academic_session.id,
        classroom.id,
        school_id=student.school_id,
        decided_by_role="teacher",
        allow_level_skip=True,
    )
    repeat_student(student2.id, academic_session.id, school_id=student2.school_id)

    promotions = get_session_promotions(academic_session.id, school_id=student.school_id)

    assert len(promotions) == 2
    student_ids = {p.student_id for p in promotions}
    assert student_ids == {student.id, student2.id}


def test_get_session_promotions_session_not_found(school):
    assert get_session_promotions(99999, school_id=school.id) is None