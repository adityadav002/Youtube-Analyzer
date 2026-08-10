from flask import Blueprint, request, jsonify
from app.services.channel_service import ChannelService
from app.schemas.channel_schema import ChannelSchema, ChannelCreateSchema, ChannelUpdateSchema

channel_bp = Blueprint('channels', __name__, url_prefix='/api/channels')
channel_schema = ChannelSchema()
channels_schema = ChannelSchema(many=True)

@channel_bp.route('', methods=['GET'])
def get_channels():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'name')
    
    items, total = ChannelService.get_channels(page, per_page, sort_by)
    return jsonify({
        'items': channels_schema.dump(items),
        'total': total,
        'page': page,
        'per_page': per_page
    })



@channel_bp.route('/<channel_id>', methods=['GET'])

def get_channel(channel_id):
    channel = ChannelService.get_channel(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    return jsonify(channel_schema.dump(channel))

@channel_bp.route('', methods=['POST'])
def add_channel():
    schema = ChannelCreateSchema()
    errors = schema.validate(request.json)
    if errors:
        return jsonify({'errors': errors}), 422
        
    job_id = ChannelService.add_channel(request.json['url'])
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202

@channel_bp.route('/<channel_id>', methods=['PATCH'])
def update_channel(channel_id):
    schema = ChannelUpdateSchema()
    errors = schema.validate(request.json)
    if errors:
        return jsonify({'errors': errors}), 422
        
    channel = ChannelService.update_channel(channel_id, request.json)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
    return jsonify(channel_schema.dump(channel))

@channel_bp.route('/<channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    confirm = request.args.get('confirm')
    if confirm != 'true':
        return jsonify({'error': 'Missing confirm parameter'}), 422
        
    success = ChannelService.delete_channel(channel_id)
    if not success:
        return jsonify({'error': 'Channel not found'}), 404
    return '', 204

@channel_bp.route('/<channel_id>/refresh', methods=['POST'])
def refresh_channel(channel_id):
    channel = ChannelService.get_channel(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
        
    job_id = ChannelService.add_channel(f"https://youtube.com/channel/{channel_id}")
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202

@channel_bp.route('/<channel_id>/crawl', methods=['POST'])
def crawl_channel(channel_id):
    channel = ChannelService.get_channel(channel_id)
    if not channel:
        return jsonify({'error': 'Channel not found'}), 404
        
    data = request.json or {}
    start_index = data.get('start_index', 1)
    limit = data.get('limit', 20)
    refresh_mode = data.get('refresh', False)
    load_more = data.get('load_more', False)
    
    if load_more:
        from app.models.video import Video
        from app import db
        db_video_count = db.session.query(db.func.count(Video.id)).filter(Video.channel_id == channel_id).scalar()
        start_index = db_video_count + 1
        
    from app.services.video_service import VideoService
    job_id = VideoService.crawl_channel(channel_id, start_index=start_index, limit=limit, refresh_mode=refresh_mode)
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202
