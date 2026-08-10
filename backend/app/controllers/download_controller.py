from flask import Blueprint, request, jsonify, current_app, send_file
from app import db
from app.models.history import DownloadHistory
from app.models.queue import ProcessingQueue
from app.models.video import Video
from app.utils.task_dispatcher import dispatch_task
import uuid
import os
import logging
import re
import platform
import subprocess
import shutil

logger = logging.getLogger(__name__)

download_bp = Blueprint('downloads', __name__, url_prefix='/api/downloads')

def extract_video_id(url: str):
    """
    Extracts a YouTube video ID from a URL or raw ID string.
    Returns the 11-character video ID, or None if not a valid video URL/ID.
    """
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    patterns = [
        r'(?:v=|\/v\/|embed\/|shorts\/|youtu\.be\/|\/v=)([^#\&\?]{11})',
        r'^(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^#\&\?]{11})',
        r'^(?:https?:\/\/)?youtu\.be\/([^#\&\?]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                return match.group(1)
            except IndexError:
                return match.group(0)
    return None

def resolve_video(video_identifier: str) -> Video:
    """
    Resolves a YouTube URL or a video ID to a canonical Video record in our database.
    If the video does not exist, it extracts lightweight metadata and imports it,
    creating a channel stub if necessary.
    Returns the Video object or None if not found/import failed.
    """
    if not video_identifier:
        return None
    video_id = extract_video_id(video_identifier)
    if not video_id:
        return None
        
    # Check if video already exists in db
    video = db.session.query(Video).filter(Video.id == video_id).first()
    if video:
        return video
        
    # Video does not exist. Import lightweight metadata using yt-dlp.
    try:
        from app.extraction.ytdlp_client import YtdlpClient
        from app.models.channel import Channel
        
        url = f"https://youtube.com/watch?v={video_id}"
        client = YtdlpClient()
        video_data = client.extract_video_metadata(url)
        
        channel_id = video_data.get('channel_id')
        if not channel_id:
            logger.error("Failed to extract channel_id from video metadata")
            return None
            
        # Check channel existence
        channel = db.session.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            channel_name = video_data.pop('channel_name', 'YouTube Channel')
            channel = Channel(
                id=channel_id,
                display_name=channel_name
            )
            db.session.add(channel)
            db.session.commit()
            logger.info(f"Created lightweight channel stub for channel {channel_id}")
            
            # Queue profile metadata extraction to populate channel details properly in the background
            try:
                from app.services.channel_service import ChannelService
                ChannelService.add_channel(f"https://www.youtube.com/channel/{channel_id}")
                logger.info(f"Queued profile extraction for newly created channel stub {channel_id}")
            except Exception as ce:
                logger.warning(f"Failed to queue profile extraction for channel stub {channel_id}: {ce}")
        else:
            video_data.pop('channel_name', None)
            
        # Create Video record
        video = Video(**video_data)
        db.session.add(video)
        db.session.commit()
        logger.info(f"Imported lightweight video record for video {video_id}")
        return video
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to resolve/import video for identifier {video_identifier}: {str(e)}")
        return None

@download_bp.route('', methods=['POST'])
def start_download():
    data = request.json or {}
    url = data.get('url')
    if isinstance(url, str):
        url = url.strip()
    download_type = data.get('download_type', 'video')  # video, audio, subtitle, thumbnail
    quality = data.get('quality', 'best')
    format_option = data.get('format', 'mp4')
    
    if download_type == 'subtitle':
        return jsonify({
            'success': False,
            'message': 'Subtitle downloads are no longer supported.'
        }), 400
    
    # Structured Request Logging
    logger.info(
        f"Download Request received:\n"
        f"  Payload: {data}\n"
        f"  URL/ID: {url}\n"
        f"  Type: {download_type}\n"
        f"  Quality/Lang: {quality}\n"
        f"  Format: {format_option}"
    )
    
    if not url:
        logger.warning("Download validation failed: URL or Video ID is missing")
        return jsonify({
            'success': False,
            'message': 'URL or Video ID is required'
        }), 400
        
    video_id = extract_video_id(url)
    if not video_id:
        logger.warning(f"Download validation failed: URL/ID '{url}' is in an invalid format")
        return jsonify({
            'success': False,
            'message': 'Invalid YouTube URL or Video ID format'
        }), 400

        
    # Resolve video (ensures it is either fetched from DB or newly imported from YouTube)
    video = resolve_video(url)
    if not video:
        return jsonify({
            'success': False,
            'message': f"Failed to resolve video '{video_id}'. Please make sure it is a valid, public YouTube video."
        }), 404
        
    video_id = video.id

    # Check disk space (507)
    try:
        download_dir = current_app.config.get('DOWNLOAD_DIR') or os.path.join(os.getcwd(), 'downloads')
        path_to_check = download_dir if os.path.exists(download_dir) else os.getcwd()
        total, used, free = shutil.disk_usage(path_to_check)
        if free < 500 * 1024 * 1024:
            logger.warning(f"Download blocked: Insufficient disk space ({free / (1024 * 1024):.2f} MB free)")
            return jsonify({
                'success': False,
                'message': 'Insufficient disk space'
            }), 507
    except Exception as e:
        logger.warning(f"Failed to check disk usage: {str(e)}")

    # Check if already completed and exists on disk (409)
    try:
        completed_download = db.session.query(DownloadHistory).filter(
            DownloadHistory.video_id == video_id,
            DownloadHistory.download_type == download_type,
            DownloadHistory.status == 'complete'
        ).order_by(DownloadHistory.created_at.desc()).first()

        if completed_download and completed_download.file_path and os.path.exists(completed_download.file_path):
            logger.info(f"Video {video_id} type {download_type} already completed at {completed_download.file_path}")
            return jsonify({
                'success': False,
                'message': 'Already downloaded — View in history',
                'history_id': completed_download.id
            }), 409
    except Exception as e:
        logger.exception("Error checking for completed downloads")

    # Check if there is already an active job for this video_id and download_type
    try:
        active_jobs = db.session.query(ProcessingQueue).filter(
            ProcessingQueue.job_type == 'download_video',
            ProcessingQueue.status.in_(['queued', 'processing'])
        ).all()
        
        for job in active_jobs:
            if job.payload.get('video_id') == video_id and job.payload.get('download_type') == download_type:
                history_id = job.payload.get('history_id')
                if history_id:
                    history = db.session.query(DownloadHistory).get(history_id)
                    if history and history.status in ['pending', 'downloading']:
                        return jsonify({
                            'message': 'Download already in progress',
                            'job_id': job.id,
                            'history_id': history.id,
                            'status': history.status
                        }), 200
    except Exception as e:
        logger.exception("Error checking for active download jobs")

    # Initialize DownloadHistory record
    try:
        history = DownloadHistory(
            video_id=video_id,
            download_type=download_type,
            quality=quality,
            status='pending',
            progress_percent=0
        )
        db.session.add(history)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create DownloadHistory record")
        return jsonify({
            'success': False,
            'message': 'Failed to initialize download record in database'
        }), 500

    # Create ProcessingQueue job
    try:
        job_id = str(uuid.uuid4())
        job = ProcessingQueue(
            id=job_id,
            job_type='download_video',
            target_id=video_id,
            status='queued',
            payload={
                'url': f"https://youtube.com/watch?v={video_id}",
                'video_id': video_id,
                'download_type': download_type,
                'quality': quality,
                'format': format_option,
                'history_id': history.id,
                'progress_percent': 0,
                'speed': '0 B/s',
                'eta': 'Unknown'
            }
        )
        db.session.add(job)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create ProcessingQueue job")
        
        # Clean up history record since job creation failed
        try:
            db.session.delete(history)
            db.session.commit()
        except Exception:
            db.session.rollback()
            
        return jsonify({
            'success': False,
            'message': 'Failed to queue download job'
        }), 500

    from app.jobs.video_jobs import download_video_task
    dispatch_task(download_video_task, job_id, history.id)

    return jsonify({
        'job_id': job_id,
        'history_id': history.id,
        'status': 'queued'
    }), 202

@download_bp.route('', methods=['GET'])
def get_downloads():
    try:
        histories = db.session.query(DownloadHistory).order_by(DownloadHistory.created_at.desc()).all()
        
        items = []
        for h in histories:
            video = db.session.query(Video).filter(Video.id == h.video_id).first()
            video_title = video.title if video else "Downloading YouTube Video..."
            thumbnail_url = video.thumbnail_url if video else None
            
            item = {
                'id': h.id,
                'video_id': h.video_id,
                'video_title': video_title,
                'thumbnail_url': thumbnail_url,
                'download_type': h.download_type,
                'quality': h.quality,
                'file_path': h.file_path,
                'file_size_bytes': h.file_size_bytes,
                'status': h.status,
                'error_message': h.error_message,
                'progress_percent': h.progress_percent,
                'created_at': h.created_at.isoformat() if h.created_at else None,
                'updated_at': h.updated_at.isoformat() if h.updated_at else None,
                'speed': None,
                'eta': None
            }
            
            if h.status in ['pending', 'downloading']:
                active_jobs = db.session.query(ProcessingQueue).filter(
                    ProcessingQueue.job_type == 'download_video',
                    ProcessingQueue.status.in_(['queued', 'processing'])
                ).all()
                for j in active_jobs:
                    if j.payload.get('history_id') == h.id:
                        item['speed'] = j.payload.get('speed')
                        item['eta'] = j.payload.get('eta')
                        item['progress_percent'] = j.payload.get('progress_percent', h.progress_percent)
                        break
            items.append(item)
            
        return jsonify(items), 200
    except Exception as e:
        logger.exception("Failed to query download history")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve download history'
        }), 500

@download_bp.route('/<int:download_id>/cancel', methods=['POST'])
def cancel_download(download_id):
    history = db.session.query(DownloadHistory).get(download_id)
    if not history:
        return jsonify({'error': 'Download record not found'}), 404
        
    if history.status in ['complete', 'failed', 'cancelled']:
        return jsonify({'error': f"Cannot cancel a job with status '{history.status}'"}), 400
        
    try:
        history.status = 'cancelled'
        
        active_jobs = db.session.query(ProcessingQueue).filter(
            ProcessingQueue.job_type == 'download_video',
            ProcessingQueue.status.in_(['queued', 'processing'])
        ).all()
        
        for j in active_jobs:
            if j.payload.get('history_id') == download_id:
                j.status = 'cancelled'
                
                if current_app.config.get('USE_CELERY'):
                    try:
                        from app.jobs.celery_app import celery_app
                        celery_app.control.revoke(j.id, terminate=True)
                    except Exception as ce:
                        logger.warning(f"Failed to revoke celery task {j.id}: {str(ce)}")
                break
                
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to cancel download job")
        return jsonify({'error': 'Failed to cancel download'}), 500
    
    from app.jobs.video_jobs import cleanup_temp_files
    download_dir = current_app.config.get('DOWNLOAD_DIR') or os.path.join(os.getcwd(), 'downloads')
    cleanup_temp_files(download_dir, history.video_id)
    
    return jsonify({'status': 'cancelled'}), 200

@download_bp.route('/<int:download_id>/retry', methods=['POST'])
def retry_download(download_id):
    history = db.session.query(DownloadHistory).get(download_id)
    if not history:
        return jsonify({'error': 'Download record not found'}), 404
        
    if history.download_type == 'subtitle':
        return jsonify({'error': 'Subtitle downloads are no longer supported.'}), 400
        
    if history.status not in ['failed', 'cancelled']:
        return jsonify({'error': f"Cannot retry a job with status '{history.status}'"}), 400
        
    try:
        prev_job = db.session.query(ProcessingQueue).filter(
            ProcessingQueue.job_type == 'download_video',
            ProcessingQueue.target_id == history.video_id
        ).order_by(ProcessingQueue.created_at.desc()).first()
        
        format_option = prev_job.payload.get('format', 'mp4') if prev_job else 'mp4'
        
        history.status = 'pending'
        history.progress_percent = 0
        history.error_message = None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to reset history record for retry")
        return jsonify({'error': 'Failed to queue download retry'}), 500
    
    try:
        job_id = str(uuid.uuid4())
        job = ProcessingQueue(
            id=job_id,
            job_type='download_video',
            target_id=history.video_id,
            status='queued',
            payload={
                'url': f"https://youtube.com/watch?v={history.video_id}",
                'video_id': history.video_id,
                'download_type': history.download_type,
                'quality': history.quality,
                'format': format_option,
                'history_id': history.id,
                'progress_percent': 0,
                'speed': '0 B/s',
                'eta': 'Unknown'
            }
        )
        db.session.add(job)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to create ProcessingQueue job for retry")
        return jsonify({'error': 'Failed to queue download retry'}), 500
    
    from app.jobs.video_jobs import download_video_task
    dispatch_task(download_video_task, job_id, history.id)
    
    return jsonify({
        'job_id': job_id,
        'history_id': history.id,
        'status': 'queued'
    }), 202

@download_bp.route('/<int:download_id>/file', methods=['GET'])
def download_file(download_id):
    history = db.session.query(DownloadHistory).get(download_id)
    if not history:
        return jsonify({'error': 'Download record not found'}), 404
        
    if history.status != 'complete' or not history.file_path:
        return jsonify({'error': 'Download file is not ready or failed'}), 400
        
    if not os.path.exists(history.file_path):
        return jsonify({'error': 'Download file not found on disk'}), 404
        
    download_dir = current_app.config.get('DOWNLOAD_DIR') or os.path.join(os.getcwd(), 'downloads')
    abs_file_path = os.path.abspath(history.file_path)
    abs_download_dir = os.path.abspath(download_dir)
    if not abs_file_path.startswith(abs_download_dir):
        return jsonify({'error': 'Access denied'}), 403
        
    return send_file(history.file_path, as_attachment=True)

@download_bp.route('/<int:download_id>/open', methods=['POST'])
def open_file_location(download_id):
    history = db.session.query(DownloadHistory).get(download_id)
    if not history:
        return jsonify({'error': 'Download record not found'}), 404
        
    if not history.file_path or not os.path.exists(history.file_path):
        return jsonify({'error': 'File not found on disk'}), 404
        
    try:
        file_path = os.path.abspath(history.file_path)
        sys_type = platform.system()
        
        if sys_type == 'Windows':
            subprocess.run(['explorer', '/select,', file_path])
        elif sys_type == 'Darwin':
            subprocess.run(['open', '-R', file_path])
        else:
            subprocess.run(['xdg-open', os.path.dirname(file_path)])
            
        return '', 204
    except Exception as e:
        logger.exception("Failed to open file location")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/<int:download_id>', methods=['DELETE'])
def delete_download(download_id):
    history = db.session.query(DownloadHistory).get(download_id)
    if not history:
        return jsonify({'error': 'Download record not found'}), 404
        
    delete_file_arg = request.args.get('delete_file', 'false').lower() == 'true'
    
    if delete_file_arg and history.file_path and os.path.exists(history.file_path):
        try:
            os.remove(history.file_path)
            logger.info(f"Deleted downloaded file from disk: {history.file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete downloaded file from disk: {str(e)}")
            
    try:
        db.session.delete(history)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.exception("Failed to delete DownloadHistory record")
        return jsonify({'error': 'Failed to delete record'}), 500
        
    return '', 204


