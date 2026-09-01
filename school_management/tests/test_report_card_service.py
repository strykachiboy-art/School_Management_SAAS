import pytest

from werkzeug.exceptions import (
    BadRequest,
    Forbidden,
    NotFound,
)

from school_app.enums.reportcard import ReportCardStatus
from school_app.models.reportcard import ReportCard
from school_app.modules.grading.services.report_card_service import (
    ReportCardService,
)


# ======================================================================
# generate_or_calculate
# ======================================================================

def test_generate_or_calculate_creates_report_card(
    app,
    db_session,
    school,
    student,
    academic_session,
    term,
    monkeypatch,
):
    expected_summary = {
        "subject_scores": {
            "1": {
                "score": 85.0,
                "grade": "A",
                "remark": "Excellent",
            }
        },
        "overall_average": 85.0,
        "grade": "A",
        "remark": "Excellent",
    }

    monkeypatch.setattr(
        "school_app.modules.grading.services.report_card_service.calculate_student_term_grades",
        lambda **kwargs: expected_summary,
    )

    with app.app_context():
        report = ReportCardService.generate_or_calculate(
            student_id=student.id,
            school_id=school.id,
            session_id=academic_session.id,
            term_id=term.id,
        )

        assert report.id is not None
        assert report.school_id == school.id
        assert report.student_id == student.id
        assert report.academic_session_id == academic_session.id
        assert report.term_id == term.id
        assert report.status == ReportCardStatus.CALCULATED
        assert report.summary_data == expected_summary
        assert report.public_reference

        saved = db_session.get(
            ReportCard,
            report.id,
        )

        assert saved is not None
        assert saved.summary_data == expected_summary
        assert saved.status == ReportCardStatus.CALCULATED


def test_generate_or_calculate_updates_existing_report_card(
    app,
    db_session,
    make_report_card,
    school,
    student,
    academic_session,
    term,
    monkeypatch,
):
    original_summary = {
        "overall_average": 50.0,
        "grade": "C",
    }

    new_summary = {
        "subject_scores": {},
        "overall_average": 82.5,
        "grade": "A",
        "remark": "Excellent",
    }

    existing = make_report_card(
        status=ReportCardStatus.DRAFT,
        summary_data=original_summary,
    )

    monkeypatch.setattr(
        "school_app.modules.grading.services.report_card_service.calculate_student_term_grades",
        lambda **kwargs: new_summary,
    )

    with app.app_context():
        report = ReportCardService.generate_or_calculate(
            student_id=student.id,
            school_id=school.id,
            session_id=academic_session.id,
            term_id=term.id,
        )

        assert report.id == existing.id
        assert report.status == ReportCardStatus.CALCULATED
        assert report.summary_data == new_summary

        count = (
            db_session.query(ReportCard)
            .filter_by(
                school_id=school.id,
                student_id=student.id,
                academic_session_id=academic_session.id,
                term_id=term.id,
            )
            .count()
        )

        assert count == 1


def test_generate_or_calculate_passes_school_id_to_grade_service(
    app,
    school,
    student,
    academic_session,
    term,
    monkeypatch,
):
    received = {}

    def fake_calculate(**kwargs):
        received.update(kwargs)
        return {
            "subject_scores": {},
            "overall_average": 0.0,
            "grade": "N/A",
            "remark": "No results found",
        }

    monkeypatch.setattr(
        "school_app.modules.grading.services.report_card_service.calculate_student_term_grades",
        fake_calculate,
    )

    with app.app_context():
        ReportCardService.generate_or_calculate(
            student_id=student.id,
            school_id=school.id,
            session_id=academic_session.id,
            term_id=term.id,
        )

    assert received == {
        "student_id": student.id,
        "term_id": term.id,
        "school_id": school.id,
    }


# ======================================================================
# transition_status
# ======================================================================

@pytest.mark.parametrize(
    "current_status,target_status,role",
    [
        (
            ReportCardStatus.DRAFT,
            ReportCardStatus.CALCULATED,
            "teacher",
        ),
        (
            ReportCardStatus.CALCULATED,
            ReportCardStatus.REVIEWED,
            "head_teacher",
        ),
        (
            ReportCardStatus.REVIEWED,
            ReportCardStatus.APPROVED,
            "principal",
        ),
        (
            ReportCardStatus.APPROVED,
            ReportCardStatus.PUBLISHED,
            "admin",
        ),
        (
            ReportCardStatus.PUBLISHED,
            ReportCardStatus.UNPUBLISHED,
            "admin",
        ),
        (
            ReportCardStatus.PUBLISHED,
            ReportCardStatus.ARCHIVED,
            "admin",
        ),
        (
            ReportCardStatus.UNPUBLISHED,
            ReportCardStatus.PUBLISHED,
            "admin",
        ),
        (
            ReportCardStatus.UNPUBLISHED,
            ReportCardStatus.ARCHIVED,
            "admin",
        ),
    ],
)
def test_transition_status_allows_valid_transitions(
    app,
    make_report_card,
    current_status,
    target_status,
    role,
):
    report = make_report_card(
        status=current_status,
    )

    with app.app_context():
        updated = ReportCardService.transition_status(
            report_id=report.id,
            target_status=target_status,
            user_role=role,
        )

        assert updated.status == target_status


@pytest.mark.parametrize(
    "current_status,target_status",
    [
        (
            ReportCardStatus.DRAFT,
            ReportCardStatus.REVIEWED,
        ),
        (
            ReportCardStatus.DRAFT,
            ReportCardStatus.APPROVED,
        ),
        (
            ReportCardStatus.CALCULATED,
            ReportCardStatus.PUBLISHED,
        ),
        (
            ReportCardStatus.REVIEWED,
            ReportCardStatus.PUBLISHED,
        ),
        (
            ReportCardStatus.APPROVED,
            ReportCardStatus.REVIEWED,
        ),
        (
            ReportCardStatus.ARCHIVED,
            ReportCardStatus.PUBLISHED,
        ),
    ],
)
def test_transition_status_rejects_invalid_transition(
    app,
    make_report_card,
    current_status,
    target_status,
):
    report = make_report_card(
        status=current_status,
    )

    with app.app_context():
        with pytest.raises(BadRequest):
            ReportCardService.transition_status(
                report_id=report.id,
                target_status=target_status,
                user_role="admin",
            )


@pytest.mark.parametrize(
    "target_status,unauthorized_role",
    [
        (
            ReportCardStatus.CALCULATED,
            "student",
        ),
        (
            ReportCardStatus.REVIEWED,
            "teacher",
        ),
        (
            ReportCardStatus.APPROVED,
            "teacher",
        ),
        (
            ReportCardStatus.PUBLISHED,
            "principal",
        ),
        (
            ReportCardStatus.UNPUBLISHED,
            "teacher",
        ),
        (
            ReportCardStatus.ARCHIVED,
            "teacher",
        ),
    ],
)
def test_transition_status_rejects_unauthorized_role(
    app,
    make_report_card,
    target_status,
    unauthorized_role,
):
    previous_status = {
        ReportCardStatus.CALCULATED: ReportCardStatus.DRAFT,
        ReportCardStatus.REVIEWED: ReportCardStatus.CALCULATED,
        ReportCardStatus.APPROVED: ReportCardStatus.REVIEWED,
        ReportCardStatus.PUBLISHED: ReportCardStatus.APPROVED,
        ReportCardStatus.UNPUBLISHED: ReportCardStatus.PUBLISHED,
        ReportCardStatus.ARCHIVED: ReportCardStatus.PUBLISHED,
    }[target_status]

    report = make_report_card(
        status=previous_status,
    )

    with app.app_context():
        with pytest.raises(Forbidden):
            ReportCardService.transition_status(
                report_id=report.id,
                target_status=target_status,
                user_role=unauthorized_role,
            )


def test_transition_status_report_not_found(
    app,
):
    with app.app_context():
        with pytest.raises(NotFound):
            ReportCardService.transition_status(
                report_id=999999,
                target_status=ReportCardStatus.CALCULATED,
                user_role="admin",
            )


# ======================================================================
# set_access_pin
# ======================================================================

@pytest.mark.parametrize(
    "pin",
    [
        "",
        "1",
        "12",
        "123",
        None,
    ],
)
def test_set_access_pin_rejects_short_pin(
    app,
    report_card,
    pin,
):
    with app.app_context():
        with pytest.raises(BadRequest):
            ReportCardService.set_access_pin(
                report_id=report_card.id,
                raw_pin=pin,
            )


def test_set_access_pin_sets_hashed_pin(
    app,
    db_session,
    report_card,
):
    with app.app_context():
        updated = ReportCardService.set_access_pin(
            report_id=report_card.id,
            raw_pin="1234",
        )

        assert updated.access_pin_hash
        assert updated.access_pin_hash != "1234"
        assert updated.check_access_pin("1234")
        assert not updated.check_access_pin("9999")


def test_set_access_pin_updates_existing_pin(
    app,
    report_card,
):
    report_card.set_access_pin("1234")

    with app.app_context():
        updated = ReportCardService.set_access_pin(
            report_id=report_card.id,
            raw_pin="5678",
        )

        assert updated.check_access_pin("5678")
        assert not updated.check_access_pin("1234")


def test_set_access_pin_report_not_found(
    app,
):
    with app.app_context():
        with pytest.raises(NotFound):
            ReportCardService.set_access_pin(
                report_id=999999,
                raw_pin="1234",
            )


# ======================================================================
# verify_and_fetch_public
# ======================================================================

def test_verify_public_published_without_pin(
    app,
    published_report_card,
):
    with app.app_context():
        report = ReportCardService.verify_and_fetch_public(
            public_ref=published_report_card.public_reference,
        )

        assert report.id == published_report_card.id
        assert report.status == ReportCardStatus.PUBLISHED


def test_verify_public_published_with_correct_pin(
    app,
    published_report_card_with_pin,
):
    with app.app_context():
        report = ReportCardService.verify_and_fetch_public(
            public_ref=published_report_card_with_pin.public_reference,
            raw_pin="1234",
        )

        assert report.id == published_report_card_with_pin.id


def test_verify_public_rejects_wrong_pin(
    app,
    published_report_card_with_pin,
):
    with app.app_context():
        with pytest.raises(Forbidden):
            ReportCardService.verify_and_fetch_public(
                public_ref=published_report_card_with_pin.public_reference,
                raw_pin="9999",
            )


def test_verify_public_rejects_missing_pin_when_pin_required(
    app,
    published_report_card_with_pin,
):
    with app.app_context():
        with pytest.raises(Forbidden):
            ReportCardService.verify_and_fetch_public(
                public_ref=published_report_card_with_pin.public_reference,
                raw_pin=None,
            )


@pytest.mark.parametrize(
    "status",
    [
        ReportCardStatus.DRAFT,
        ReportCardStatus.CALCULATED,
        ReportCardStatus.REVIEWED,
        ReportCardStatus.APPROVED,
        ReportCardStatus.UNPUBLISHED,
        ReportCardStatus.ARCHIVED,
    ],
)
def test_verify_public_rejects_non_published_report(
    app,
    make_report_card,
    status,
):
    report = make_report_card(
        status=status,
    )

    with app.app_context():
        with pytest.raises(NotFound):
            ReportCardService.verify_and_fetch_public(
                public_ref=report.public_reference,
            )


def test_verify_public_rejects_unknown_reference(
    app,
):
    with app.app_context():
        with pytest.raises(NotFound):
            ReportCardService.verify_and_fetch_public(
                public_ref="does-not-exist",
            )