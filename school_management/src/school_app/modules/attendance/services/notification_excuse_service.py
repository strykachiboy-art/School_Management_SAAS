import logging

logger = logging.getLogger(__name__)


def notify_excuse_decision(excuse):

    student = excuse.attendance.student
    recipient_email = getattr(student, "email", None) or getattr(student.user, "email", None)

    logger.info(
        "Excuse #%s for student #%s %s (notify: %s)",
        excuse.id,
        excuse.attendance.student_id,
        excuse.status.value,
        recipient_email or "no email on file",
    )