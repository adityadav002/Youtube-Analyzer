from flask import Blueprint, request, jsonify
from app.services.video_service import VideoService
from app.schemas.video_schema import VideoSchema

video_bp = Blueprint('videos', __name__)
video_schema = VideoSchema()
videos_schema = VideoSchema(many=True)

def parse_boolean(val):
    if val is None:
        return None
    val_lower = str(val).lower()
    if val_lower in ['true', '1', 't', 'y', 'yes']:
        return True
    if val_lower in ['false', '0', 'f', 'n', 'no']:
        return False
    return None

@video_bp.route('', methods=['GET'])
def get_videos():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'upload_date')
    sort_order = request.args.get('sort_order', 'desc')
    channel_id = request.args.get('channel_id')
    search_query = request.args.get('q')
    
    is_short = parse_boolean(request.args.get('is_short'))
    is_live = parse_boolean(request.args.get('is_live'))
    
    items, total = VideoService.get_videos(page, per_page, sort_by, sort_order, channel_id, search_query, is_short, is_live)
    
    serialized_videos = videos_schema.dump(items)
    has_more = total > (page * per_page)
    next_cursor = str(page + 1) if has_more else None
    
    return jsonify({
        'items': serialized_videos,
        'total': total,
        'page': page,
        'per_page': per_page,
        
        'videos': serialized_videos,
        'has_more': has_more,
        'next_cursor': next_cursor,
        'total_loaded': len(items)
    })

@video_bp.route('', methods=['POST'])
def import_video():
    data = request.json or {}
    url = data.get('url') or data.get('video_id')
    if not url:
        return jsonify({'error': 'video_id or url is required'}), 400
    
    # Validate that the identifier is actually a video URL/ID before attempting import
    from app.controllers.download_controller import extract_video_id, resolve_video
    video_id = extract_video_id(url)
    if not video_id:
        return jsonify({
            'error': 'Invalid video identifier',
            'message': 'The provided value is not a valid YouTube video URL or video ID. '
                       'Channels and playlists cannot be imported as videos.'
        }), 400
    
    try:
        video = resolve_video(url)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception(f"Unexpected error resolving video '{url}'")
        return jsonify({
            'error': 'Failed to import video',
            'message': str(e)
        }), 500
    
    if not video:
        return jsonify({
            'error': 'Failed to import video',
            'message': f"Could not resolve or import video '{video_id}'. "
                       'Please ensure it is a valid, public YouTube video.'
        }), 404
        
    return jsonify(video_schema.dump(video)), 201

@video_bp.route('/<video_id>', methods=['GET'])

def get_video(video_id):
    video = VideoService.get_video(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    return jsonify(video_schema.dump(video))

@video_bp.route('/<video_id>/extract', methods=['POST'])
def extract_metadata(video_id):
    video = VideoService.get_video(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404
        
    job_id = VideoService.extract_metadata(video_id)
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202

@video_bp.route('/<video_id>', methods=['DELETE'])
def delete_video(video_id):
    success = VideoService.delete_video(video_id)
    if success:
        return '', 204
    return jsonify({'error': 'Video not found'}), 404

@video_bp.route('/<video_id>/download', methods=['GET'])
def download_video(video_id):
    from app.controllers.download_controller import handle_direct_download
    return handle_direct_download(video_id)
