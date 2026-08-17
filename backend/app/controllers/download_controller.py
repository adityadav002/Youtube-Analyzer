from flask import Blueprint, request, jsonify, current_app, send_file, Response
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
        from app.services.youtube_api_service import YouTubeApiService
        from app.models.channel import Channel
        
        api_service = YouTubeApiService()
        video_data = api_service.fetch_video_metadata(video_id)
        
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
    cleanup_temp_files(download_dir, history.id)
    
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

def get_safe_filename(history):
    video = db.session.query(Video).filter(Video.id == history.video_id).first()
    title = video.title if video else f"download_{history.video_id}"
    from yt_dlp.utils import sanitize_filename
    safe_title = sanitize_filename(title)
    
    ext = 'mp4'
    if history.download_type == 'audio':
        try:
            prev_job = db.session.query(ProcessingQueue).filter(
                ProcessingQueue.job_type == 'download_video',
                ProcessingQueue.target_id == history.video_id
            ).order_by(ProcessingQueue.created_at.desc()).first()
            ext = prev_job.payload.get('format', 'mp3') if prev_job else 'mp3'
        except Exception:
            ext = 'mp3'
    elif history.download_type == 'thumbnail':
        ext = 'jpg'
        if history.file_path:
            _, ext_part = os.path.splitext(history.file_path)
            if ext_part:
                ext = ext_part.lstrip('.')
    return f"{safe_title}.{ext}"

def stream_file_generator(file_path, history_id, app):
    try:
        logger.info(f"Starting file stream for history {history_id}: {file_path}")
        # Stream the file content
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192 * 16) # 128KB chunk
                if not chunk:
                    break
                yield chunk
                
    except GeneratorExit:
        logger.info(f"Stream connection closed by client for history {history_id}. Initiating cancellation/cleanup.")
        try:
            with app.app_context():
                from app import db
                from app.models.history import DownloadHistory
                from app.models.queue import ProcessingQueue
                
                history = db.session.query(DownloadHistory).get(history_id)
                if history and history.status not in ['complete', 'failed', 'cancelled']:
                    history.status = 'cancelled'
                    db.session.commit()
                    
                # Cancel the queue job
                if history:
                    job = db.session.query(ProcessingQueue).filter(
                        ProcessingQueue.job_type == 'download_video',
                        ProcessingQueue.target_id == history.video_id,
                        ProcessingQueue.status.in_(['queued', 'processing'])
                    ).order_by(ProcessingQueue.created_at.desc()).first()
                    if job:
                        job.status = 'cancelled'
                        db.session.commit()
        except Exception as ex:
            logger.warning(f"Failed to cancel history/job on client disconnect: {ex}")
        raise
        
    except Exception as e:
        logger.exception(f"Error during stream generation for history {history_id}: {e}")
        raise
        
    finally:
        # Always clean up the physical file from the disk once streaming finishes or fails
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Successfully deleted temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {file_path}: {e}")
                
        # Always clean up associated temp ytdl/part files for this download ID
        try:
            with app.app_context():
                download_dir = app.config.get('DOWNLOAD_DIR') or os.path.join(os.getcwd(), 'downloads')
                from app.jobs.video_jobs import cleanup_temp_files
                cleanup_temp_files(download_dir, history_id)
        except Exception as e:
            logger.warning(f"Failed to clean up temp files for history {history_id}: {e}")

@download_bp.route('/<int:download_id>/file', methods=['GET'])
def download_file(download_id):
    import time
    from flask import stream_with_context
    
    history = db.session.query(DownloadHistory).get(download_id)
    if not history:
        return jsonify({'error': 'Download record not found'}), 404
        
    # Check if physical file exists. If it does not exist (e.g. deleted or Windows path),
    # we reset the status and start a new background task to download it.
    if not history.file_path or not os.path.exists(history.file_path):
        # Reset database history and queue task
        try:
            # First check if there is already an active job running for this history record
            active_jobs = db.session.query(ProcessingQueue).filter(
                ProcessingQueue.job_type == 'download_video',
                ProcessingQueue.status.in_(['queued', 'processing'])
            ).all()
            
            is_already_running = False
            for job in active_jobs:
                if job.payload.get('history_id') == history.id:
                    is_already_running = True
                    break
                    
            if not is_already_running:
                logger.info(f"Physical file missing for completed history {download_id}. Re-triggering download.")
                history.status = 'pending'
                history.progress_percent = 0
                history.error_message = None
                db.session.commit()
                
                # Retrieve format from previous job payload if possible
                format_option = 'mp4'
                try:
                    prev_job = db.session.query(ProcessingQueue).filter(
                        ProcessingQueue.job_type == 'download_video',
                        ProcessingQueue.target_id == history.video_id
                    ).order_by(ProcessingQueue.created_at.desc()).first()
                    if prev_job:
                        format_option = prev_job.payload.get('format', 'mp4')
                except Exception:
                    pass
                    
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
                
                from app.jobs.video_jobs import download_video_task
                dispatch_task(download_video_task, job_id, history.id)
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Failed to reset/start download for streaming: {e}")
            return jsonify({'error': 'Failed to initiate stream download'}), 500
            
    # Wait for the download task to complete (under Flask request context)
    start_time = time.time()
    while True:
        db.session.expire_all()
        history = db.session.query(DownloadHistory).get(download_id)
        if not history:
            return jsonify({'error': 'Download record deleted'}), 404
            
        if history.status == 'complete':
            break
            
        if history.status in ['failed', 'cancelled']:
            return jsonify({'error': f"Download failed: {history.error_message or 'Unknown error'}"}), 400
            
        if time.time() - start_time > 600: # 10 minutes timeout
            return jsonify({'error': 'Download timeout'}), 504
            
        time.sleep(0.5)

    # Extract required database values before streaming starts
    file_path = history.file_path
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': f"Downloaded file not found on disk: {file_path}"}), 404
        
    filename = get_safe_filename(history)
    app_instance = current_app._get_current_object()

    # Return streaming response
    try:
        return Response(
            stream_with_context(stream_file_generator(file_path, history.id, app_instance)),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        logger.exception(f"Failed to stream download: {e}")
        return jsonify({'error': str(e)}), 500

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

def stream_file_generator_direct(file_path):
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(128 * 1024)
                if not chunk:
                    break
                yield chunk
    finally:
        # Always clean up the temporary file immediately after response completes or fails
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Successfully cleaned up temporary direct download file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary direct download file {file_path}: {e}")

class DirectProgressHook:
    """Progress hook for synchronous direct downloads.
    
    Updates DownloadHistory.progress_percent in the database every ~2 seconds
    so the GET /api/downloads polling endpoint can return live progress to the UI.
    """
    def __init__(self, history_id):
        self.history_id = history_id
        self.last_update = 0
        self.last_pct = -1

    def __call__(self, d):
        import time
        status = d.get('status')
        if status != 'downloading':
            return

        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes') or 0
        pct = int(downloaded * 100 / total) if total > 0 else 0

        now = time.time()
        if now - self.last_update < 2.0 and pct == self.last_pct:
            return
        self.last_update = now
        self.last_pct = pct

        try:
            history = db.session.query(DownloadHistory).get(self.history_id)
            if history:
                history.progress_percent = pct
                history.status = 'downloading'
                db.session.commit()
        except Exception:
            db.session.rollback()

def handle_direct_download(video_id):
    import uuid
    import tempfile
    import shutil
    import yt_dlp
    from app.extraction.ytdlp_client import SafeYoutubeDL
    from datetime import datetime, timezone
    from flask import request, current_app, Response, stream_with_context, jsonify
    from yt_dlp.utils import sanitize_filename
    
    from app import db
    from app.models.history import DownloadHistory
    from app.models.video import Video
    from app.models.settings import UserSettings
    from app.jobs.video_jobs import parse_rate_limit
    
    download_type = request.args.get('download_type', 'video')
    quality = request.args.get('quality', 'best')
    format_option = request.args.get('format', 'mp4')
    
    logger.info(f"[DirectDownload] video_id={video_id}")
    logger.info(f"[DirectDownload] quality={quality}")
    logger.info(f"[DirectDownload] format={format_option}")
    logger.info(f"[DirectDownload] type={download_type}")
    
    # 1. Resolve video details
    video = resolve_video(video_id)
    if not video:
        return jsonify({
            'success': False,
            'message': f"Failed to resolve video '{video_id}'. Please make sure it is a valid, public YouTube video."
        }), 404
        
    title = video.title
    safe_title = sanitize_filename(title)
    
    ext = format_option
    if download_type == 'audio':
        ext = format_option if format_option in ['mp3', 'm4a', 'wav'] else 'mp3'
    elif download_type == 'thumbnail':
        ext = 'jpg'
    else:
        ext = 'mp4'
        
    filename_header = f"{safe_title}.{ext}"
    
    # 2. Insert metadata record in DownloadHistory
    history = DownloadHistory(
        video_id=video_id,
        download_type=download_type,
        quality=quality,
        status='downloading',
        progress_percent=0
    )
    db.session.add(history)
    db.session.commit()
    
    # 3. Retrieve User Settings
    settings = db.session.query(UserSettings).get(1)
    proxy = settings.ytdlp_proxy if settings else None
    cookies_file = settings.cookies_file_path if settings else None
    client_name = settings.ytdlp_player_client if settings else 'ios'
    rate_limit = settings.ytdlp_rate_limit if settings else None
    
    temp_path = None
    downloaded_file = None
    
    try:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"analyzer_download_{history.id}_{uuid.uuid4().hex}")
        outtmpl = f"{temp_path}.%(ext)s"
        
        if download_type == 'thumbnail':
            import requests
            from urllib.parse import urlparse
            
            thumb_url = video.thumbnail_url if video else f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            
            # Determine extension
            ext_val = 'jpg'
            if thumb_url:
                parsed_url = urlparse(thumb_url)
                url_ext = os.path.splitext(parsed_url.path)[1]
                if url_ext:
                    ext_val = url_ext.lstrip('.')
            if ext_val not in ['jpg', 'png', 'webp', 'jpeg']:
                ext_val = 'jpg'
                
            filename_header = f"{safe_title}.{ext_val}"
            downloaded_file = f"{temp_path}.{ext_val}"
            
            # Check local file
            is_copied = False
            if thumb_url and thumb_url.startswith('/thumbnails/'):
                local_filename = thumb_url.replace('/thumbnails/', '')
                thumbnail_dir = current_app.config.get('THUMBNAIL_DIR') or os.path.join(os.getcwd(), 'thumbnails')
                local_path = os.path.join(thumbnail_dir, local_filename)
                if os.path.exists(local_path):
                    try:
                        shutil.copy(local_path, downloaded_file)
                        is_copied = True
                        logger.info(f"[DirectDownload] Copied local thumbnail from {local_path} to {downloaded_file}")
                    except Exception as copy_err:
                        logger.warning(f"[DirectDownload] Failed to copy local thumbnail: {copy_err}")
            
            if not is_copied:
                if not thumb_url or thumb_url.startswith('/thumbnails/'):
                    thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                
                logger.info(f"[DirectDownload] Downloading remote thumbnail from {thumb_url} to {downloaded_file}")
                res = requests.get(thumb_url, stream=True, timeout=15)
                if res.status_code == 404 and 'maxresdefault' in thumb_url:
                    thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                    logger.info(f"[DirectDownload] maxresdefault not found. Retrying with hqdefault: {thumb_url}")
                    res = requests.get(thumb_url, stream=True, timeout=15)
                
                res.raise_for_status()
                with open(downloaded_file, 'wb') as f:
                    shutil.copyfileobj(res.raw, f)
            
            file_size = os.path.getsize(downloaded_file)
            
            # Update history metadata to complete
            history.status = 'complete'
            history.file_size_bytes = file_size
            history.progress_percent = 100
            db.session.commit()
            
            logger.info(f"[DirectDownload] Thumbnail downloaded successfully. Size: {file_size}")
            
            # Determine proper MIME type
            mime_map = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp'}
            mime_type = mime_map.get(ext_val.lower(), 'image/jpeg')
            
            response = send_file(
                downloaded_file,
                mimetype=mime_type,
                as_attachment=True,
                download_name=filename_header
            )
            
            temp_file_to_clean = downloaded_file
            @response.call_on_close
            def cleanup_temp_file():
                if temp_file_to_clean and os.path.exists(temp_file_to_clean):
                    try:
                        os.remove(temp_file_to_clean)
                        logger.info(f"[DirectDownload] cleanup completed: {temp_file_to_clean}")
                    except Exception as cleanup_err:
                        logger.warning(f"[DirectDownload] cleanup failed for {temp_file_to_clean}: {cleanup_err}")
            
            return response
            
        ffmpeg_available = shutil.which('ffmpeg') is not None
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'outtmpl': outtmpl,
        }
        
        from app.extraction.ytdlp_client import configure_ytdlp_options
        configure_ytdlp_options(ydl_opts, settings)
            
        if rate_limit:
            parsed_limit = parse_rate_limit(rate_limit)
            if parsed_limit:
                ydl_opts['ratelimit'] = parsed_limit
                
        # Format selection
        if download_type == 'video':
            if quality == 'best':
                if ffmpeg_available:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                else:
                    ydl_opts['format'] = 'best'
            elif quality in ['1080p', '720p', '480p']:
                h = quality.replace('p', '')
                if ffmpeg_available:
                    ydl_opts['format'] = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]'
                else:
                    ydl_opts['format'] = f'best[height<={h}]'
            else:
                ydl_opts['format'] = 'best'
                
            ydl_opts['merge_output_format'] = format_option
            
        elif download_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            if ffmpeg_available:
                audio_quality_map = {
                    '128k': '128',
                    '192k': '192',
                    '256k': '256',
                    '320k': '320'
                }
                preferred_quality = audio_quality_map.get(quality, '192')
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_option if format_option in ['mp3', 'm4a', 'wav'] else 'mp3',
                    'preferredquality': preferred_quality,
                }]
            else:
                raise Exception("ffmpeg is required for audio extraction but was not found.")
                
        # Execute download synchronously to temp folder
        url = f"https://youtube.com/watch?v={video_id}"
        ydl_opts['progress_hooks'] = [DirectProgressHook(history.id)]
        logger.info("[DirectDownload] starting yt-dlp")
        logger.info(f"Direct stream download starting for {url} with options {ydl_opts}")
        
        with SafeYoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename_from_ydl = ydl.prepare_filename(info_dict)
        
        base_name, _ = os.path.splitext(filename_from_ydl)
        final_ext = format_option if download_type in ['video', 'audio'] else 'mp4'
        if download_type == 'audio' and ffmpeg_available:
            final_ext = format_option
            
        # Check actual file path on disk
        downloaded_file = filename_from_ydl
        if not os.path.exists(downloaded_file):
            for ext_candidate in [final_ext, 'mp4', 'mkv', 'webm', 'mp3', 'm4a', 'wav']:
                p = f"{base_name}.{ext_candidate}"
                if os.path.exists(p):
                    downloaded_file = p
                    break
                        
        if not downloaded_file or not os.path.exists(downloaded_file) or os.path.getsize(downloaded_file) == 0:
            raise Exception("Downloaded file not found or is empty.")
            
        file_size = os.path.getsize(downloaded_file)
        
        # Update history metadata to complete
        history.status = 'complete'
        history.file_size_bytes = file_size
        db.session.commit()
        
        logger.info(f"[DirectDownload] file exists before response: True")
        logger.info(f"[DirectDownload] file size: {file_size}")
        
        # Determine proper MIME type
        mime_type = 'video/mp4'
        if download_type == 'audio':
            mime_map = {'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'wav': 'audio/wav'}
            mime_type = mime_map.get(ext, 'audio/mpeg')
        
        # Use Flask's send_file which properly streams from disk,
        # sets Content-Length, and does NOT load the entire file into RAM.
        response = send_file(
            downloaded_file,
            mimetype=mime_type,
            as_attachment=True,
            download_name=filename_header
        )
        
        # Register cleanup to run AFTER the response has been fully sent to the browser.
        # call_on_close fires only after WSGI finishes writing all bytes to the client.
        temp_file_to_clean = downloaded_file
        @response.call_on_close
        def cleanup_temp_file():
            if temp_file_to_clean and os.path.exists(temp_file_to_clean):
                try:
                    os.remove(temp_file_to_clean)
                    logger.info(f"[DirectDownload] cleanup completed: {temp_file_to_clean}")
                except Exception as cleanup_err:
                    logger.warning(f"[DirectDownload] cleanup failed for {temp_file_to_clean}: {cleanup_err}")
        
        logger.info(f"[DirectDownload] response Content-Length: {file_size}")
        logger.info(f"[DirectDownload] response Content-Type: {mime_type}")
        logger.info(f"[DirectDownload] response Content-Disposition: attachment; filename=\"{filename_header}\"")
        logger.info("[DirectDownload] returning send_file response")
        
        return response
        
    except Exception as e:
        logger.exception(f"Direct stream download failed for {video_id}: {e}")
        db.session.rollback()
        
        # Clean up temp file immediately if it exists
        if downloaded_file and os.path.exists(downloaded_file):
            try:
                os.remove(downloaded_file)
            except Exception:
                pass
                
        # Clean up other potential temp files matching temp_path
        if temp_path:
            try:
                for f in os.listdir(temp_dir):
                    if f.startswith(os.path.basename(temp_path)):
                        try:
                            os.remove(os.path.join(temp_dir, f))
                        except Exception:
                            pass
            except Exception:
                pass
                
        err_msg = str(e)
        err_lower = err_msg.lower()
        
        category = "DOWNLOAD_ERROR"
        status_code = 500
        user_msg = f"Failed to download video: {err_msg}"
        
        if any(msg in err_lower for msg in ["confirm you're not a bot", "confirm you’re not a bot", "sign in to confirm", "not a bot", "login_required"]):
            category = "YOUTUBE_AUTHENTICATION_REQUIRED"
            status_code = 403
            user_msg = "YouTube requires authentication for this download."
        elif "age restricted" in err_lower or "age-restricted" in err_lower or "confirm your age" in err_lower:
            category = "AGE_RESTRICTED"
            status_code = 403
            user_msg = "This video is age-restricted and requires age verification."
        elif "private video" in err_lower:
            category = "PRIVATE_VIDEO"
            status_code = 403
            user_msg = "This video is private on YouTube."
        elif "video unavailable" in err_lower or "not available" in err_lower or "unavailable" in err_lower:
            category = "VIDEO_UNAVAILABLE"
            status_code = 404
            user_msg = "This video is unavailable on YouTube."
        elif "requested format not available" in err_lower or "no video formats" in err_lower or "format not available" in err_lower:
            category = "FORMAT_UNAVAILABLE"
            status_code = 400
            user_msg = "The requested quality or format is not available for this video."
        elif "ffmpeg" in err_lower:
            category = "FFMPEG_ERROR"
            status_code = 500
            user_msg = "An error occurred in FFmpeg while merging or processing media formats."
        elif "network" in err_lower or "connection" in err_lower or "http error" in err_lower:
            category = "NETWORK_ERROR"
            status_code = 502
            user_msg = "A network error occurred while communicating with YouTube."
            
        history.status = 'failed'
        history.error_message = f"{category}: {user_msg}"
        db.session.commit()
        
        return jsonify({
            'success': False,
            'category': category,
            'message': user_msg
        }), status_code


