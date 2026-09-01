import pytest
from werkzeug.exceptions import HTTPException
from datetime import time

from school_app.models.timetable import Timetable
from school_app.modules.classrooms.services.timetable_service import (
    create_timetable,
    get_timetable,
    get_timetables,
    update_timetable,
    delete_timetable,
    get_teacher_timetable,
    get_classroom_timetable,
)


# ======================================================================
# Create
# ======================================================================

def test_create_timetable_success(
    app,
    db_session,
    term,
    classroom,
    subject,
    teacher,
):
    with app.app_context():
        data = {
            "term_id": term.id,
            "classroom_id": classroom.id,
            "subject_id": subject.id,
            "teacher_id": teacher.id,
            "day_of_week": "MONDAY",
            "start_time": time(8, 0),
            "end_time": time(9, 0),
        }

        timetable = create_timetable(
            data,
            school_id=term.school_id,
        )

        assert timetable.id is not None
        assert timetable.school_id == term.school_id
        assert timetable.term_id == term.id
        assert timetable.classroom_id == classroom.id
        assert timetable.subject_id == subject.id
        assert timetable.teacher_id == teacher.id
        assert timetable.start_time == time(8, 0)
        assert timetable.end_time == time(9, 0)


def test_create_timetable_invalid_time(
    app,
    term,
    classroom,
    subject,
    teacher,
):
    with app.app_context():
        data = {
            "term_id": term.id,
            "classroom_id": classroom.id,
            "subject_id": subject.id,
            "teacher_id": teacher.id,
            "day_of_week": "MONDAY",
            "start_time": time(10, 0),
            "end_time": time(9, 0),
        }

        with pytest.raises(HTTPException) as exc_info:
            create_timetable(
                data,
                school_id=term.school_id,
            )

        assert exc_info.value.code == 400


def test_create_timetable_term_from_wrong_school(
    app,
    term,
    classroom,
    subject,
    teacher,
):
    with app.app_context():
        data = {
            "term_id": 999999,
            "classroom_id": classroom.id,
            "subject_id": subject.id,
            "teacher_id": teacher.id,
            "day_of_week": "MONDAY",
            "start_time": time(8, 0),
            "end_time": time(9, 0),
        }

        with pytest.raises(HTTPException) as exc_info:
            create_timetable(
                data,
                school_id=term.school_id,
            )

        assert exc_info.value.code == 404


def test_create_timetable_teacher_from_wrong_school(
    app,
    term,
    classroom,
    subject,
    teacher,
):
    with app.app_context():
        data = {
            "term_id": term.id,
            "classroom_id": classroom.id,
            "subject_id": subject.id,
            "teacher_id": 999999,
            "day_of_week": "MONDAY",
            "start_time": time(8, 0),
            "end_time": time(9, 0),
        }

        with pytest.raises(HTTPException) as exc_info:
            create_timetable(
                data,
                school_id=term.school_id,
            )

        assert exc_info.value.code == 404


# ======================================================================
# Schedule Conflicts
# ======================================================================

def test_create_timetable_teacher_conflict(
    app,
    timetable,
):
    with app.app_context():
        data = {
            "term_id": timetable.term_id,
            "classroom_id": timetable.classroom_id,
            "subject_id": timetable.subject_id,
            "teacher_id": timetable.teacher_id,
            "day_of_week": timetable.day_of_week,
            "start_time": time(8, 30),
            "end_time": time(9, 30),
        }

        with pytest.raises(HTTPException) as exc_info:
            create_timetable(
                data,
                school_id=timetable.school_id,
            )

        assert exc_info.value.code == 409
        assert "Teacher is already scheduled" in str(
            exc_info.value.description
        )


def test_create_timetable_classroom_conflict(
    app,
    timetable,
    second_teacher,
):
    with app.app_context():
        # Same classroom and overlapping time,
        # but deliberately use a different teacher so
        # the classroom conflict is the one detected.
        assert second_teacher.id != timetable.teacher_id

        data = {
            "term_id": timetable.term_id,
            "classroom_id": timetable.classroom_id,
            "subject_id": timetable.subject_id,
            "teacher_id": second_teacher.id,
            "day_of_week": timetable.day_of_week,
            "start_time": time(8, 30),
            "end_time": time(9, 30),
        }

        with pytest.raises(HTTPException) as exc_info:
            create_timetable(
                data,
                school_id=timetable.school_id,
            )

        assert exc_info.value.code == 409
        assert "Classroom is already occupied" in str(
            exc_info.value.description
        )


# ======================================================================
# Get Single
# ======================================================================

def test_get_timetable_success(
    app,
    timetable,
):
    with app.app_context():
        result = get_timetable(
            timetable.id,
            school_id=timetable.school_id,
        )

        assert result.id == timetable.id
        assert result.school_id == timetable.school_id


def test_get_timetable_wrong_school(
    app,
    timetable,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            get_timetable(
                timetable.id,
                school_id=999999,
            )

        assert exc_info.value.code == 404


# ======================================================================
# Get Timetables
# ======================================================================

def test_get_timetables_success(
    app,
    timetable,
):
    with app.app_context():
        pagination = get_timetables(
            school_id=timetable.school_id,
            page=1,
            per_page=10,
        )

        assert pagination.total >= 1
        assert any(
            item.id == timetable.id
            for item in pagination.items
        )


def test_get_timetables_are_school_scoped(
    app,
    timetable,
):
    with app.app_context():
        pagination = get_timetables(
            school_id=timetable.school_id,
            page=1,
            per_page=100,
        )

        assert all(
            item.school_id == timetable.school_id
            for item in pagination.items
        )


def test_get_timetables_filter_by_term(
    app,
    timetable,
):
    with app.app_context():
        pagination = get_timetables(
            school_id=timetable.school_id,
            term_id=timetable.term_id,
            page=1,
            per_page=10,
        )

        assert all(
            item.term_id == timetable.term_id
            for item in pagination.items
        )


# ======================================================================
# Update
# ======================================================================

def test_update_timetable_success(
    app,
    timetable,
):
    with app.app_context():
        data = {
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        updated = update_timetable(
            timetable.id,
            data,
            school_id=timetable.school_id,
        )

        assert updated.id == timetable.id
        assert updated.start_time == time(10, 0)
        assert updated.end_time == time(11, 0)


def test_update_timetable_invalid_time(
    app,
    timetable,
):
    with app.app_context():
        data = {
            "start_time": time(12, 0),
            "end_time": time(11, 0),
        }

        with pytest.raises(HTTPException) as exc_info:
            update_timetable(
                timetable.id,
                data,
                school_id=timetable.school_id,
            )

        assert exc_info.value.code == 400


def test_update_timetable_wrong_school(
    app,
    timetable,
):
    with app.app_context():
        data = {
            "start_time": time(10, 0),
            "end_time": time(11, 0),
        }

        with pytest.raises(HTTPException) as exc_info:
            update_timetable(
                timetable.id,
                data,
                school_id=999999,
            )

        assert exc_info.value.code == 404


# ======================================================================
# Delete
# ======================================================================

def test_delete_timetable_success(
    app,
    db_session,
    timetable,
):
    with app.app_context():
        timetable_id = timetable.id
        school_id = timetable.school_id

        result = delete_timetable(
            timetable_id,
            school_id=school_id,
        )

        assert result is True

        deleted = db_session.get(
            Timetable,
            timetable_id,
        )

        assert deleted is None


def test_delete_timetable_wrong_school(
    app,
    timetable,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            delete_timetable(
                timetable.id,
                school_id=999999,
            )

        assert exc_info.value.code == 404


# ======================================================================
# Teacher Timetable
# ======================================================================

def test_get_teacher_timetable_success(
    app,
    timetable,
):
    with app.app_context():
        results = get_teacher_timetable(
            timetable.teacher_id,
            school_id=timetable.school_id,
            term_id=timetable.term_id,
        )

        assert isinstance(results, list)

        assert all(
            item.teacher_id == timetable.teacher_id
            for item in results
        )

        assert all(
            item.school_id == timetable.school_id
            for item in results
        )


def test_get_teacher_timetable_wrong_school(
    app,
    timetable,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            get_teacher_timetable(
                timetable.teacher_id,
                school_id=999999,
            )

        assert exc_info.value.code == 404


# ======================================================================
# Classroom Timetable
# ======================================================================

def test_get_classroom_timetable_success(
    app,
    timetable,
):
    with app.app_context():
        results = get_classroom_timetable(
            timetable.classroom_id,
            school_id=timetable.school_id,
            term_id=timetable.term_id,
        )

        assert isinstance(results, list)

        assert all(
            item.classroom_id == timetable.classroom_id
            for item in results
        )

        assert all(
            item.school_id == timetable.school_id
            for item in results
        )


def test_get_classroom_timetable_wrong_school(
    app,
    timetable,
):
    with app.app_context():
        with pytest.raises(HTTPException) as exc_info:
            get_classroom_timetable(
                timetable.classroom_id,
                school_id=999999,
            )

        assert exc_info.value.code == 404
