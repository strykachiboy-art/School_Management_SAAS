from flask import jsonify
from school_app.decorators import role_required
from school_app.modules.school.routes.admin_core_route import admin_bp
from school_app.modules.admin_reports.services.admin_report_services import get_admin_report
from school_app.enums.role import Role


@admin_bp.route("/report", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_route():
    report = get_admin_report()
    return jsonify(report), 200