from flask import Blueprint, request, jsonify
from app.services.search_service import SearchService
from app.extraction.ytdlp_client import YtdlpError, YtdlpRateLimitError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)

def parse_boolean(val):
    if val is None:
        return False
    val_lower = str(val).lower()
    return val_lower in ['true', '1', 't', 'y', 'yes']

@search_bp.route('/youtube', methods=['GET'])
def search_youtube():
    q = request.args.get('q')
    if not q:
        return jsonify({'error': "Query parameter 'q' is required"}), 422
        
    search_type = request.args.get('type', 'video')
    if search_type not in ['video', 'channel', 'playlist']:
        search_type = 'video'
        
    max_results = request.args.get('max_results', 20, type=int)
    if max_results not in [10, 20, 50]:
        max_results = 20
        
    refresh = parse_boolean(request.args.get('refresh'))
    
    try:
        results = SearchService.search_youtube(
            query=q,
            search_type=search_type,
            max_results=max_results,
            refresh=refresh
        )
        return jsonify(results)
    except YtdlpRateLimitError as e:
        logger.warning(f"YouTube search rate limit or bot detection for query '{q}': {str(e)}")
        return jsonify({
            'error': "YouTube search temporarily unavailable",
            'message': "YouTube has rate-limited searches or triggered bot detection. Please try again later."
        }), 503
    except YtdlpError as e:
        logger.error(f"YouTube search yt-dlp execution failure for query '{q}': {str(e)}")
        return jsonify({
            'error': "YouTube search execution failure",
            'message': f"yt-dlp search failed: {str(e)}"
        }), 502
    except SQLAlchemyError as e:
        logger.exception(f"Database error during YouTube search for query '{q}': {str(e)}")
        return jsonify({
            'error': "Database error",
            'message': "A database error occurred while querying or saving search history. Please check database logs."
        }), 500
    except Exception as e:
        logger.exception(f"Unexpected search error for query '{q}': {str(e)}")
        return jsonify({
            'error': "Unexpected search error",
            'message': str(e)
        }), 500


@search_bp.route('/internal', methods=['GET'])
def search_internal():
    q = request.args.get('q')
    if not q:
        return jsonify({'error': "Query parameter 'q' is required"}), 422
        
    search_type = request.args.get('type', 'video')
    if search_type not in ['video', 'channel', 'transcript']:
        search_type = 'video'
        
    channel_id = request.args.get('channel_id')
    has_transcript = request.args.get('has_transcript') # 'yes' | 'no' | 'any'
    is_short = request.args.get('is_short') # 'yes' | 'no' | 'any'
    upload_after = request.args.get('upload_after') # YYYY-MM-DD
    upload_before = request.args.get('upload_before') # YYYY-MM-DD
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    try:
        results = SearchService.search_internal(
            query=q,
            search_type=search_type,
            channel_id=channel_id,
            has_transcript=has_transcript,
            is_short=is_short,
            upload_after=upload_after,
            upload_before=upload_before,
            page=page,
            per_page=per_page
        )
        return jsonify(results)
    except Exception as e:
        logger.exception(f"Internal search error for query '{q}': {str(e)}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@search_bp.route('/history', methods=['GET'])
def search_history():
    try:
        limit = request.args.get('limit', 20, type=int)
        history = SearchService.get_search_history(limit=limit)
        return jsonify(history)
    except Exception as e:
        logger.error(f"Error fetching search history: {str(e)}")
        return jsonify({'error': 'Failed to fetch search history'}), 500
