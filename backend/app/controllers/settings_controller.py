from flask import Blueprint, request, jsonify
from app.models import UserSettings, Channel, Video, DownloadHistory, Comment, Transcript
from app import db
import os

settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

def get_db_size():
    try:
        from sqlalchemy import text
        if 'mysql' in str(db.engine.url):
            res = db.session.execute(text(
                "SELECT SUM(data_length + index_length) "
                "FROM information_schema.tables "
                "WHERE table_schema = :db_name"
            ), {'db_name': db.engine.url.database}).scalar()
            return int(res) if res else 0
        return 0
    except Exception:
        return 0

@settings_bp.route('', methods=['GET'])
def get_settings():
    try:
        settings = db.session.query(UserSettings).get(1)
        if not settings:
            settings = UserSettings(id=1)
            db.session.add(settings)
            db.session.commit()
            
        counts = {
            'channels': db.session.query(Channel).count(),
            'videos': db.session.query(Video).count(),
            'downloads': db.session.query(DownloadHistory).count(),
            'comments': db.session.query(Comment).count(),
            'transcripts': db.session.query(Transcript).count(),
        }
        
        db_size_bytes = get_db_size()
        
        return jsonify({
            'settings': {
                'auto_extract_transcript': settings.auto_extract_transcript,
                'auto_extract_comments': settings.auto_extract_comments,
                'auto_extract_thumbnail': settings.auto_extract_thumbnail,
                'max_comments_per_video': settings.max_comments_per_video,
                'default_video_quality': settings.default_video_quality,
                'default_audio_format': settings.default_audio_format,
                'default_audio_quality': settings.default_audio_quality,
                'max_concurrent_downloads': settings.max_concurrent_downloads,
                'ytdlp_player_client': settings.ytdlp_player_client,
                'ytdlp_rate_limit': settings.ytdlp_rate_limit,
                'ytdlp_proxy': settings.ytdlp_proxy,
                'cookies_file_path': settings.cookies_file_path,
                'rss_poll_interval_minutes': settings.rss_poll_interval_minutes,
                'snapshot_enabled': settings.snapshot_enabled,
            },
            'db_stats': {
                'counts': counts,
                'size_bytes': db_size_bytes
            }
        }), 200
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Failed to fetch settings")
        return jsonify({'error': 'Failed to retrieve settings'}), 500

@settings_bp.route('', methods=['PUT'])
def update_settings():
    try:
        data = request.json or {}
        settings = db.session.query(UserSettings).get(1)
        if not settings:
            settings = UserSettings(id=1)
            db.session.add(settings)
            
        for key, val in data.items():
            if hasattr(settings, key) and key != 'id':
                setattr(settings, key, val)
                
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception("Failed to update settings")
        return jsonify({'error': 'Failed to update settings'}), 500

@settings_bp.route('/cookies', methods=['POST'])
def upload_cookies():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        from flask import current_app
        base_dir = os.path.dirname(current_app.root_path)
        cookies_dir = os.path.join(base_dir, 'config')
        os.makedirs(cookies_dir, exist_ok=True)
        file_path = os.path.join(cookies_dir, 'cookies.txt')
        
        file.save(file_path)
        
        settings = db.session.query(UserSettings).get(1)
        if not settings:
            settings = UserSettings(id=1)
            db.session.add(settings)
        settings.cookies_file_path = file_path
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cookies file uploaded successfully',
            'path': file_path
        }), 200
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Failed to upload cookies")
        return jsonify({'error': 'Failed to upload cookies'}), 500

@settings_bp.route('/cookies', methods=['DELETE'])
def delete_cookies():
    try:
        settings = db.session.query(UserSettings).get(1)
        if settings and settings.cookies_file_path:
            if os.path.exists(settings.cookies_file_path):
                try:
                    os.remove(settings.cookies_file_path)
                except Exception:
                    pass
            settings.cookies_file_path = None
            db.session.commit()
            
        return jsonify({
            'success': True,
            'message': 'Cookies file deleted successfully'
        }), 200
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).exception("Failed to delete cookies")
        return jsonify({'error': 'Failed to delete cookies'}), 500

@settings_bp.route('/cookies/test', methods=['POST'])
def test_cookies():
    try:
        settings = db.session.query(UserSettings).get(1)
        if not settings or not settings.cookies_file_path or not os.path.exists(settings.cookies_file_path):
            return jsonify({'valid': False, 'message': 'No cookies file found on disk'}), 404
            
        with open(settings.cookies_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            header = f.readline()
            if 'netscape' in header.lower() or '# http' in header.lower() or '\t' in header:
                return jsonify({'valid': True, 'message': 'Cookies file is in valid Netscape format'}), 200
            else:
                return jsonify({'valid': False, 'message': 'File does not appear to be in Netscape format'}), 200
    except Exception as e:
        return jsonify({'valid': False, 'message': f'Failed to test cookies: {str(e)}'}), 500
