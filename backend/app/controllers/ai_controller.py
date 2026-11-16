from flask import Blueprint, request, jsonify
from app.services.ai_service import AIAnalysisService, AIAnalysisError
import logging

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__, url_prefix='/api/ai')

@ai_bp.route('/status', methods=['GET'])
def ai_status():
    return jsonify({
        'enabled': AIAnalysisService.is_enabled(),
        'provider': 'gemini',
        'model': 'gemini-1.5-flash'
    })

@ai_bp.route('/analysis/<video_id>', methods=['GET'])
def get_video_analysis(video_id):
    analysis_type = request.args.get('type', 'full')
    analysis = AIAnalysisService.get_analysis(video_id, analysis_type=analysis_type)
    if not analysis:
        return jsonify({
            'error': 'Analysis not found',
            'message': f"No AI analysis found for video '{video_id}'. You can trigger one via POST /api/ai/analyze/{video_id}"
        }), 404
    return jsonify(analysis)

@ai_bp.route('/analyze/<video_id>', methods=['POST'])
def analyze_video(video_id):
    payload = request.get_json(silent=True) or {}
    analysis_type = payload.get('type', 'full')
    try:
        result = AIAnalysisService.analyze_video(video_id, analysis_type=analysis_type)
        return jsonify(result), 200
    except AIAnalysisError as e:
        return jsonify({
            'error': 'AI Analysis Error',
            'message': e.message
        }), e.status_code
    except Exception as e:
        logger.exception(f"Unexpected error analyzing video {video_id}: {e}")
        return jsonify({
            'error': 'Unexpected error',
            'message': str(e)
        }), 500
