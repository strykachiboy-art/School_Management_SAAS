from flask import Blueprint, jsonify, request
from school_app.decorators import role_required
from school_app.enums.role import Role

from school_app.modules.admin_reports.services.admin_report_services import get_admin_report_overview
from school_app.modules.admin_reports.services.admin_report_academic_service import get_admin_report_academic
from school_app.modules.admin_reports.services.admin_report_attendance_service import get_admin_report_attendance
from school_app.modules.admin_reports.services.admin_report_classrooms_service import get_admin_report_classrooms
from school_app.modules.admin_reports.services.admin_report_students_service import get_admin_report_students
from school_app.modules.admin_reports.services.admin_report_teachers_service import get_admin_report_teachers
from school_app.modules.admin_reports.services.admin_report_fees_service import get_admin_report_fees

from school_app.modules.admin_reports.requests.admin_report_request import (
    AcademicReportFilters,
    AttendanceReportFilters,
    ClassroomsReportFilters,
    StudentsReportFilters,
    TeachersReportFilters,
    FeesReportFilters,
)

reports_bp = Blueprint("admin_reports", __name__, url_prefix="/reports")


@reports_bp.route("/overview", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_overview_route():
    report = get_admin_report_overview()
    return jsonify(report), 200


@reports_bp.route("/academic", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_academic_route():
    # ValidationError from a bad param (e.g. non-numeric session_id)
    # bubbles to the app's global handler -> clean 400, no try/except needed here.
    filters = AcademicReportFilters.model_validate(request.args.to_dict())
    report = get_admin_report_academic(
        session_id=filters.session_id, classroom_id=filters.classroom_id,
        subject_id=filters.subject_id,
    )
    return jsonify(report), 200


@reports_bp.route("/attendance", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_attendance_route():
    filters = AttendanceReportFilters.model_validate(request.args.to_dict())
    report = get_admin_report_attendance(
        session_id=filters.session_id, term_id=filters.term_id, classroom_id=filters.classroom_id,
        student_id=filters.student_id, start_date=filters.start_date, end_date=filters.end_date,
        page=filters.page, page_size=filters.page_size,
    )
    return jsonify(report), 200


@reports_bp.route("/classrooms", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_classrooms_route():
    filters = ClassroomsReportFilters.model_validate(request.args.to_dict())
    report = get_admin_report_classrooms(session_id=filters.session_id, term_id=filters.term_id)
    return jsonify(report), 200


@reports_bp.route("/students", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_students_route():
    filters = StudentsReportFilters.model_validate(request.args.to_dict())
    report = get_admin_report_students(
        classroom_id=filters.classroom_id, gender=filters.gender, session_id=filters.session_id,
        term_id=filters.term_id, is_active=filters.is_active,
        start_date=filters.start_date, end_date=filters.end_date,
        page=filters.page, page_size=filters.page_size,
    )
    return jsonify(report), 200


@reports_bp.route("/teachers", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_teachers_route():
    filters = TeachersReportFilters.model_validate(request.args.to_dict())
    report = get_admin_report_teachers(
        gender=filters.gender, subject_id=filters.subject_id,
        classroom_id=filters.classroom_id, is_active=filters.is_active,
    )
    return jsonify(report), 200


@reports_bp.route("/fees", methods=["GET"])
@role_required(Role.ADMIN)
def get_admin_report_fees_route():
    filters = FeesReportFilters.model_validate(request.args.to_dict())
    report = get_admin_report_fees(
        session_id=filters.session_id, term_id=filters.term_id, classroom_id=filters.classroom_id,
        student_id=filters.student_id, start_date=filters.start_date, end_date=filters.end_date,
    )
    return jsonify(report), 200