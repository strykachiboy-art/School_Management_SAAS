import smtplib
from email.message import EmailMessage
from flask import current_app


def send_email(to: str, subject: str, body: str) -> bool:
    """Best-effort send — never raises, since a bad email shouldn't break the request."""
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = current_app.config["MAIL_FROM"]
        msg["To"] = to
        msg.set_content(body)

        with smtplib.SMTP(current_app.config["MAIL_HOST"], current_app.config["MAIL_PORT"]) as smtp:
            if current_app.config.get("MAIL_USE_TLS"):
                smtp.starttls()
            if current_app.config.get("MAIL_USERNAME"):
                smtp.login(current_app.config["MAIL_USERNAME"], current_app.config["MAIL_PASSWORD"])
            smtp.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception(f"Failed to send email to {to}")
        return False