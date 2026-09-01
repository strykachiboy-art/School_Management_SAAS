from school_app.extensions import db
from school_app.enums.reportcard import ReportCardStatus
from school_app.models.reportcard import ReportCard
from school_app.modules.grading.services.grade_service import (
    calculate_student_term_grades,
)
from werkzeug.exceptions import (
    Forbidden,
    BadRequest,
    NotFound,
)


# ======================================================================
# Allowed workflow transitions
# ======================================================================

ALLOWED_TRANSITIONS = {
    ReportCardStatus.DRAFT: [
        ReportCardStatus.CALCULATED,
    ],
    ReportCardStatus.CALCULATED: [
        ReportCardStatus.REVIEWED,
        ReportCardStatus.DRAFT,
    ],
    ReportCardStatus.REVIEWED: [
        ReportCardStatus.APPROVED,
        ReportCardStatus.DRAFT,
    ],
    ReportCardStatus.APPROVED: [
        ReportCardStatus.PUBLISHED,
        ReportCardStatus.DRAFT,
    ],
    ReportCardStatus.PUBLISHED: [
        ReportCardStatus.UNPUBLISHED,
        ReportCardStatus.ARCHIVED,
    ],
    ReportCardStatus.UNPUBLISHED: [
        ReportCardStatus.PUBLISHED,
        ReportCardStatus.ARCHIVED,
    ],
    ReportCardStatus.ARCHIVED: [],
}


# ======================================================================
# Role permissions
# ======================================================================

REQUIRED_ROLES = {
    ReportCardStatus.CALCULATED: [
        "teacher",
        "head_teacher",
        "admin",
    ],
    ReportCardStatus.REVIEWED: [
        "head_teacher",
        "admin",
    ],
    ReportCardStatus.APPROVED: [
        "principal",
        "admin",
    ],
    ReportCardStatus.PUBLISHED: [
        "admin",
    ],
    ReportCardStatus.UNPUBLISHED: [
        "admin",
    ],
    ReportCardStatus.ARCHIVED: [
        "admin",
    ],
}


class ReportCardService:

    # ==================================================================
    # Generate / Calculate
    # ==================================================================

    @staticmethod
    def generate_or_calculate(
        student_id: int,
        school_id: int,
        session_id: int,
        term_id: int,
    ) -> ReportCard:
        """
        Fetch an existing report card or create one.

        The student's term grades are calculated and stored as a
        snapshot in summary_data.

        The report card is then moved to CALCULATED.
        """

        report = (
            db.session.query(ReportCard)
            .filter_by(
                school_id=school_id,
                student_id=student_id,
                academic_session_id=session_id,
                term_id=term_id,
            )
            .first()
        )

        if report is None:
            report = ReportCard(
                school_id=school_id,
                student_id=student_id,
                academic_session_id=session_id,
                term_id=term_id,
                status=ReportCardStatus.DRAFT,
            )

            db.session.add(report)

        summary = calculate_student_term_grades(
            student_id=student_id,
            term_id=term_id,
            school_id=school_id,
        )

        report.summary_data = summary
        report.status = ReportCardStatus.CALCULATED

        db.session.commit()
        db.session.refresh(report)

        return report

    # ==================================================================
    # Status transition
    # ==================================================================

    @staticmethod
    def transition_status(
        report_id: int,
        target_status: ReportCardStatus,
        user_role: str,
    ) -> ReportCard:
        """
        Validate the requested status transition and role permission.
        """

        report = db.session.get(
            ReportCard,
            report_id,
        )

        if report is None:
            raise NotFound(
                "Report card not found."
            )

        allowed_transitions = ALLOWED_TRANSITIONS.get(
            report.status,
            [],
        )

        if target_status not in allowed_transitions:
            raise BadRequest(
                f"Invalid transition from "
                f"{report.status.value} to "
                f"{target_status.value}."
            )

        allowed_roles = REQUIRED_ROLES.get(
            target_status,
            ["admin"],
        )

        if user_role not in allowed_roles:
            raise Forbidden(
                "You do not have permission to perform "
                "this status transition."
            )

        report.status = target_status

        db.session.commit()
        db.session.refresh(report)

        return report

    # ==================================================================
    # Set PIN
    # ==================================================================

    @staticmethod
    def set_access_pin(
        report_id: int,
        raw_pin: str,
    ) -> ReportCard:
        """
        Set or update the report-card access PIN.
        """

        if not raw_pin or len(raw_pin) < 4:
            raise BadRequest(
                "PIN must be at least 4 characters long."
            )

        report = db.session.get(
            ReportCard,
            report_id,
        )

        if report is None:
            raise NotFound(
                "Report card not found."
            )

        report.set_access_pin(
            raw_pin
        )

        db.session.commit()
        db.session.refresh(report)

        return report

    # ==================================================================
    # Public verification
    # ==================================================================

    @staticmethod
    def verify_and_fetch_public(
        public_ref: str,
        raw_pin: str = None,
    ) -> ReportCard:
        """
        Fetch a published report card using its public reference.

        If a PIN is configured, the supplied PIN must be valid.
        """

        report = (
            db.session.query(ReportCard)
            .filter_by(
                public_reference=public_ref,
            )
            .first()
        )

        if (
            report is None
            or report.status != ReportCardStatus.PUBLISHED
        ):
            raise NotFound(
                "Report card not found or is not currently published."
            )

        if report.access_pin_hash:
            if not report.check_access_pin(
                raw_pin or ""
            ):
                raise Forbidden(
                    "Invalid access PIN for this report card."
                )

        return report