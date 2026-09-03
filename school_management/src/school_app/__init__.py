"""School management application package."""
from typing import Optional
from flask import Flask, g, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from school_app.models.user import User
from school_app.errors import register_error_handlers

from .config import get_config_class
from .extensions import cors, db, jwt, limiter, migrate


def create_app(config: Optional[dict] = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(get_config_class())

    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    
    from school_app.modules.classrooms.routes.subject_route import subject_bp
    from school_app.modules.classrooms.routes.classroom_route import classroom_bp
    from school_app.modules.classrooms.routes.assignment_route import ass_bp
    from school_app.modules.people.routes.teacher_route import teacher_bp
    from school_app.modules.people.routes.student_route import student_bp
    from school_app.modules.grading.routes.exam_route import exam_bp
    from school_app.modules.grading.routes.result_route import result_bp
    from school_app.modules.school.routes.admin_core_route import admin_bp
    from school_app.modules.grading.routes.teacher_grade_route import teacher_grade_bp
    from school_app.auth.auth import auth_bp
    from school_app.auth.routes.change_password import change_password_route
    import school_app.auth.routes.profile
    import school_app.auth.routes.forgot_password
    import school_app.modules.grading.routes.admin_grade_route
    import school_app.auth.routes.log_out
    import school_app.auth.routes.register
    import school_app.auth.routes.login
    import school_app.auth.routes.refresh_access_token
    import school_app.auth.routes.google_auth
    from school_app.modules.grading.routes.student_grade_route import student_grade_bp
    from school_app.modules.academics.routes.academic_session_route import academic_session_bp
    from school_app.modules.academics.routes.academic_stage_route import academic_stage_bp
    from school_app.modules.academics.routes.academic_level_route import academic_level_bp
    from school_app.modules.academics.routes.section_route import section_bp
    from school_app.modules.academics.routes.term_route import term_bp
    from school_app.modules.attendance.routes.attendance_route import attendance_bp
    from school_app.modules.promotion.routes.promotion_route import promotion_bp
    from school_app.modules.attendance.routes.excuse_route import excuse_bp
    from school_app.modules.classrooms.routes.timetable_route import timetable_bp
    from school_app.modules.people.routes.parent_guardian_route import parent_guardian_bp
    from school_app.modules.people.routes.teacher_permission_route import teacher_permission_bp
    from school_app.modules.notifications.routes.notification_route import notification_bp
    from school_app.modules.audit.routes.audit_route import audit_bp
    from school_app.modules.admin_reports.routes.admin_reports_route import reports_bp
    from school_app.modules.school_fees.routes.school_fees_route import school_fees_bp
    from school_app.modules.grading.routes.report_card_route import report_card_bp
    from school_app.modules.onboarding.routes.onboarding_route import onboarding_bp
    from school_app.modules.settings.routes.settings_route import settings_bp

    
    app.register_blueprint(subject_bp, url_prefix="/subjects")
    app.register_blueprint(classroom_bp, url_prefix="/classrooms")
    app.register_blueprint(ass_bp, url_prefix="/assignments")
    app.register_blueprint(teacher_bp, url_prefix="/teachers")
    app.register_blueprint(student_bp, url_prefix="/students")
    app.register_blueprint(exam_bp, url_prefix="/exams")
    app.register_blueprint(result_bp, url_prefix = "/results")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(teacher_grade_bp, url_prefix="/teacher")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_grade_bp, url_prefix="/student")
    app.register_blueprint(academic_session_bp, url_prefix="/academic-sessions")
    app.register_blueprint(academic_stage_bp, url_prefix="/academic-stages")
    app.register_blueprint(academic_level_bp, url_prefix="/academic-levels")
    app.register_blueprint(section_bp, url_prefix="/sections")
    app.register_blueprint(term_bp, url_prefix = "/terms")
    app.register_blueprint(attendance_bp, url_prefix = "/attendances")
    app.register_blueprint(promotion_bp, url_prefix="/promotions")

    from school_app.modules.grading.routes.grading_system_route import grading_system_bp, grading_rule_bp
    from school_app.modules.promotion.routes.promotion_rule_route import promotion_rule_bp
    from school_app.modules.school.routes.school_route import school_bp
    app.register_blueprint(grading_system_bp, url_prefix="/grading-systems")
    app.register_blueprint(grading_rule_bp, url_prefix="/grading-rules")
    app.register_blueprint(promotion_rule_bp, url_prefix="/promotion-rules")
    app.register_blueprint(school_bp, url_prefix="/schools")
    app.register_blueprint(excuse_bp, url_prefix="/excuses")
    app.register_blueprint(timetable_bp, url_prefix="/timetables")
    app.register_blueprint(parent_guardian_bp, url_prefix="/parent-guardians")
    app.register_blueprint(teacher_permission_bp, url_prefix="/admin/teachers")
    app.register_blueprint(notification_bp, url_prefix="/notifications")
    app.register_blueprint(audit_bp, url_prefix="/audit-logs")
    app.register_blueprint(reports_bp, url_prefix="/admin/reports")
    app.register_blueprint(school_fees_bp, url_prefix="/fees")
    app.register_blueprint(report_card_bp, url_prefix="/report-cards")
    app.register_blueprint(onboarding_bp, url_prefix="/onboarding")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    
    
    register_error_handlers(app)

    @app.before_request
    def load_current_user():
        if request.endpoint == "auth.refresh":
            g.user = None
            return

        try:
           verify_jwt_in_request(optional=True)
           user_id = get_jwt_identity()
           if user_id:
              g.user = db.session.get(User, user_id)
           else:
              g.user = None
        except Exception:
           g.user = None

    @app.after_request
    def after(response):
        return response

    _register_cli_commands(app)

    return app


def _register_cli_commands(app):
    import click

    @app.cli.command("backfill-sections")
    @click.option("--dry-run", is_flag=True, default=False, help="Preview without writing changes.")
    def backfill_sections_command(dry_run):
        """Assign Classroom.section_id for classrooms still on the old
        deprecated `level` int, by creating a default re-nameable
        Stage/Level/Section structure. Run with --dry-run first to preview."""
        from school_app.modules.classrooms.services.backfill_service import backfill_classroom_sections

        result = backfill_classroom_sections(dry_run=dry_run)

        label = "[DRY RUN] " if dry_run else ""
        click.echo(f"{label}Backfilled {len(result['backfilled'])} classroom(s).")
        for entry in result["backfilled"]:
            if dry_run:
                click.echo(f"  {entry['classroom_name']} (level {entry['old_level']}) -> {entry['would_assign_section']}")
            else:
                click.echo(f"  {entry['classroom_name']} (level {entry['old_level']}) -> section_id {entry['assigned_section_id']}")

        if result["levels_created"]:
            click.echo(f"Levels created: {', '.join(result['levels_created'])}")

        if result["skipped"]:
            click.echo(f"Skipped {len(result['skipped'])} classroom(s) with no level value:")
            for entry in result["skipped"]:
                click.echo(f"  {entry['classroom_name']} — {entry['reason']}")

__all__ = ["create_app", "db"]