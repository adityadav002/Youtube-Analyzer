import logging
from flask import Blueprint, jsonify
from app import db
from app.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        data = DashboardService.get_dashboard_stats()
        return jsonify(data), 200
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to fetch dashboard statistics")
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred while retrieving stats'
        }), 500
