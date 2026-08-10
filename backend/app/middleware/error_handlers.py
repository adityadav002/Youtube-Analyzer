from flask import jsonify, request
from werkzeug.exceptions import HTTPException
import logging
import uuid

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Not found",
            "request_id": getattr(request, 'id', str(uuid.uuid4()))
        }), 404

    @app.errorhandler(422)
    def validation_error(error):
        # We will map marshmallow validation errors here later
        return jsonify({
            "error": "Validation error",
            "request_id": getattr(request, 'id', str(uuid.uuid4()))
        }), 422
        
    @app.errorhandler(Exception)
    def internal_error(error):
        if isinstance(error, HTTPException):
            return jsonify({
                "error": error.description,
                "request_id": getattr(request, 'id', str(uuid.uuid4()))
            }), error.code
            
        logger.exception("Unhandled Exception")
        return jsonify({
            "error": "Internal server error",
            "request_id": getattr(request, 'id', str(uuid.uuid4()))
        }), 500
