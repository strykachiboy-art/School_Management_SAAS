import logging
from flask import jsonify, render_template
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException
from school_app.utils.helpers import wants_json

logger = logging.getLogger(__name__)


def register_error_handlers(app):

    # 1. Generic HTTP Exception Handler (400, 404, 403, etc.)
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        # Prefer specific description passed to abort(), fallback to default HTTP status name
        message = e.description if e.description != HTTPException.description else e.name

        if wants_json():
            return jsonify({
                "error": message,
                "description": message
            }), e.code

        return render_template("errors/generic.html", error=e.name, message=message), e.code

    # 2. Pydantic Schema Validation Error Handler
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        details = [
            {"field": str(err["loc"][-1]) if err["loc"] else "unknown", "message": err["msg"]}
            for err in e.errors()
        ]
        message = "Validation failed: " + ", ".join(f'{d["field"]} - {d["message"]}' for d in details)

        if wants_json():
            return jsonify({
                "error": message,
                "description": message,
                "details": details
            }), 400 

        return render_template("errors/400.html", message=message), 22

    @app.errorhandler(ValueError)
    def handle_value_error(e):
        message = str(e)

        if wants_json():
            return jsonify({
                "error": message,
                "description": message
            }), 400

        return render_template("errors/400.html", message=message), 400

    # 4. Unhandled Internal Server Errors (500)
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        logger.exception("Unhandled server exception: %s", e)

        if wants_json():
            return jsonify({
                "error": "Internal Server Error",
                "description": "An unexpected error occurred."
            }), 500

        return render_template("errors/500.html"), 500