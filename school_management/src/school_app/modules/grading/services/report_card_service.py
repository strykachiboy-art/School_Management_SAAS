import secrets
from school_app.extensions import db
from school_app.enums.reportcard import ReportCardStatus
from school_app.models.reportcard import ReportCard
from school_app.modules.grading.services.grade_service import calculate_student_term_grades
from werkzeug.exceptions import Forbidden, BadRequest, NotFound

# Allowed workflow transitions
ALLOWED_TRANSITIONS = {
    ReportCardStatus.DRAFT: [ReportCardStatus.CALCULATED],
    ReportCardStatus.CALCULATED: [ReportCardStatus.REVIEWED, ReportCardStatus.DRAFT],
    ReportCardStatus.REVIEWED: [ReportCardStatus.APPROVED, ReportCardStatus.DRAFT],
    ReportCardStatus.APPROVED: [ReportCardStatus.PUBLISHED, ReportCardStatus.DRAFT],
    ReportCardStatus.PUBLISHED: [ReportCardStatus.UNPUBLISHED, ReportCardStatus.ARCHIVED],
    ReportCardStatus.UNPUBLISHED: [ReportCardStatus.PUBLISHED, ReportCardStatus.ARCHIVED],
    ReportCardStatus.ARCHIVED: []
}

# Role permissions for target statuses
REQUIRED_ROLES = {
    ReportCardStatus.CALCULATED: ['teacher', 'head_teacher', 'admin'],
    ReportCardStatus.REVIEWED: ['head_teacher', 'admin'],
    ReportCardStatus.APPROVED: ['principal', 'admin'],
    ReportCardStatus.PUBLISHED: ['admin'],
    ReportCardStatus.UNPUBLISHED: ['admin'],
    ReportCardStatus.ARCHIVED: ['admin']
}


class ReportCardService:

    @staticmethod
    def generate_or_calculate(student_id: int, session_id: int, term_id: int) -> ReportCard:
        """Fetch or create a report card, then pull grades from grade_service 
        to update summary_data and advance status to CALCULATED.
        """
        report = db.session.query(ReportCard).filter_by(
            student_id=student_id,
            academic_session_id=session_id,
            term_id=term_id
        ).first()

        if not report:
            report = ReportCard(
                student_id=student_id,
                academic_session_id=session_id,
                term_id=term_id,
                public_reference=secrets.token_urlsafe(16),
                status=ReportCardStatus.DRAFT
            )
            db.session.add(report)

        # Pull calculated scores and grades from grade_service
        term_summary = calculate_student_term_grades(
            student_id=student_id,
            term_id=term_id
        )

        report.summary_data = term_summary
        report.status = ReportCardStatus.CALCULATED
        db.session.commit()
        return report

    @staticmethod
    def transition_status(report_id: int, target_status: ReportCardStatus, user_role: str) -> ReportCard:
        """Enforce transition state machine and user role authorization."""
        report = db.session.get(ReportCard, report_id)
        if not report:
            raise NotFound("Report card not found.")

        if target_status not in ALLOWED_TRANSITIONS.get(report.status, []):
            raise BadRequest(f"Invalid transition from {report.status.value} to {target_status.value}.")

        allowed_roles = REQUIRED_ROLES.get(target_status, ['admin'])
        if user_role not in allowed_roles:
            raise Forbidden("You do not have permission to perform this status transition.")

        report.status = target_status
        db.session.commit()
        return report

    @staticmethod
    def set_access_pin(report_id: int, raw_pin: str) -> ReportCard:
        """Set or update the hashed verification PIN for a report card."""
        if not raw_pin or len(raw_pin) < 4:
            raise BadRequest("PIN must be at least 4 characters long.")

        report = db.session.get(ReportCard, report_id)
        if not report:
            raise NotFound("Report card not found.")

        report.set_access_pin(raw_pin)
        db.session.commit()
        return report

    @staticmethod
    def verify_and_fetch_public(public_ref: str, raw_pin: str = None) -> ReportCard:
        """Lookup published report card by public reference token and verify optional PIN."""
        report = db.session.query(ReportCard).filter_by(public_reference=public_ref).first()
        
        if not report or report.status != ReportCardStatus.PUBLISHED:
            raise NotFound("Report card not found or is not currently published.")

        if report.access_pin_hash and not report.check_access_pin(raw_pin or ""):
            raise Forbidden("Invalid access PIN for this report card.")

        return report