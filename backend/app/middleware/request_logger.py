import uuid
import logging
from flask import request

logger = logging.getLogger(__name__)

def register_request_logger(app):
    @app.before_request
    def set_request_id():
        request.id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
    @app.after_request
    def log_request(response):
        response.headers['X-Request-ID'] = getattr(request, 'id', '')
        # We can add more structured logging here later
        return response
