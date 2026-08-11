from app.jobs.celery_app import celery_app
from app.extraction.ytdlp_client import YtdlpClient
from app.repositories.video_repository import VideoRepository
from app.repositories.channel_repository import ChannelRepository
from app.models.queue import ProcessingQueue
from app.utils.thumbnail_utils import download_thumbnail
from app import db
from app.utils.task_dispatcher import dispatch_task
import logging
from app.models.video import Video
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def crawl_channel_videos_task(self, job_id: str, channel_id: str):
    job = db.session.query(ProcessingQueue).get(job_id)
    if not job:
        return
        
    job.status = 'processing'
    db.session.commit()
    
    payload = job.payload or {}
    start_index = payload.get('start_index', 1)
    limit = payload.get('limit', 20)
    refresh_mode = payload.get('refresh_mode', False)
    
    logger.info(f"Crawl progress: Starting crawl for channel {channel_id} using YouTube Data API v3 (start_index={start_index}, limit={limit}, refresh_mode={refresh_mode})")
    
    try:
        channel = ChannelRepository.get_by_id(channel_id)
        if not channel:
            raise Exception("Channel not found")

        from app.services.youtube_api_service import YouTubeApiService
        api_service = YouTubeApiService()

        # Crawl and enrich videos using the YouTube Data API
        videos_data, inserted, updated, result_counts = api_service.crawl_channel_videos(
            channel_id=channel_id,
            start_index=start_index,
            limit=limit,
            refresh_mode=refresh_mode
        )

        # Update channel statistics safely
        if channel:
            db_video_count = db.session.query(db.func.count(Video.id)).filter(Video.channel_id == channel_id).scalar() or 0
            db_view_count = db.session.query(db.func.sum(Video.view_count)).filter(Video.channel_id == channel_id).scalar() or 0
            db_join_date = db.session.query(db.func.min(Video.upload_date)).filter(Video.channel_id == channel_id).scalar()
            
            if not channel.video_count or db_video_count > channel.video_count:
                channel.video_count = db_video_count
                
            if db_view_count > 0 and (not channel.view_count or db_view_count > channel.view_count):
                channel.view_count = db_view_count
                
            if not channel.join_date and db_join_date:
                channel.join_date = db_join_date
                
            channel.last_crawled_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info("Crawl progress: Reconciled and updated channel statistics.")

        # Update job payload with the crawl result details
        current_payload = job.payload or {}
        current_payload['result'] = result_counts
        job.payload = current_payload

        job.status = 'complete'
        job.target_id = channel_id
        db.session.commit()
        
    except Exception as e:
        logger.exception(f"Failed to crawl videos for channel {channel_id}")
        db.session.rollback()
        job.status = 'failed'
        job.error_message = str(e)
        db.session.commit()

@celery_app.task(bind=True, max_retries=3)
def extract_video_metadata_task(self, job_id: str, video_id: str = None):
    # Determine the actual job and video_id
    job = None
    real_video_id = video_id
    
    if job_id:
        job = db.session.query(ProcessingQueue).get(job_id)
        if not job:
            # Fallback if job_id was actually passed as video_id
            real_video_id = job_id
            job = None

    if not real_video_id:
        logger.error("extract_video_metadata_task: No video_id provided")
        return

    if job:
        job.status = 'processing'
        db.session.commit()
        
    try:
        logger.info(f"Starting metadata extraction for video {real_video_id} using YouTube Data API v3")
        from app.services.youtube_api_service import YouTubeApiService
        api_service = YouTubeApiService()
        data = api_service.fetch_video_metadata(real_video_id)
        
        # Log metadata properties
        logger.info(
            f"Metadata extraction finished for video {real_video_id}.\n"
            f"  Title: {data.get('title')}\n"
            f"  Description Length: {len(data.get('description') or '')}\n"
            f"  Upload Date: {data.get('upload_date')}\n"
            f"  View Count: {data.get('view_count')}\n"
            f"  Thumbnail: {data.get('thumbnail_url')}\n"
            f"  Tags Count: {len(data.get('tags') or [])}"
        )
        
        # Optional: Trigger thumbnail download asynchronously
        if data.get('thumbnail_url'):
            dispatch_task(download_thumbnail_task, real_video_id, data['thumbnail_url'])
            
        existing = VideoRepository.get_by_id(real_video_id)
        if existing:
            logger.info(f"Updating video: {real_video_id} with fields: {list(data.keys())}")
            VideoRepository.update(existing, data)
        else:
            logger.info(f"Creating video: {real_video_id} with fields: {list(data.keys())}")
            VideoRepository.create(data)
            
        db.session.commit()
        logger.info(f"Commit succeeds for video {real_video_id}")
        
        # Immediately query the same row and log details to verify updated_at changed
        db.session.expire_all()  # Force reload from DB
        verified = VideoRepository.get_by_id(real_video_id)
        if verified:
            logger.info(
                f"Verification post-commit for video {real_video_id}:\n"
                f"  Saved Description: {verified.description[:60] if verified.description else None}...\n"
                f"  Saved View Count: {verified.view_count}\n"
                f"  Saved Upload Date: {verified.upload_date}\n"
                f"  Saved Updated At: {verified.updated_at}"
            )
            
            # Log classification decision
            class_name = 'NORMAL'
            if verified.is_live:
                class_name = 'LIVE'
            elif verified.is_short:
                class_name = 'SHORT'
                
            logger.info(
                f"Video ID: {verified.id}\n"
                f"Source: {verified.live_status if verified.is_live else ('shorts' if verified.is_short else 'videos')}\n"
                f"live_status: {verified.live_status}\n"
                f"duration: {verified.duration}\n"
                f"Classification: {class_name}\n"
                f"is_short={verified.is_short}\n"
                f"is_live={verified.is_live}"
            )
        
        if job:
            job.status = 'complete'
            job.target_id = real_video_id 
            db.session.commit()
            
    except Exception as e:
        logger.exception(f"Failed to extract video metadata for {real_video_id}: {str(e)}")
        db.session.rollback()
        logger.info(f"Rollback executed due to error enrichening video {real_video_id}")
        if job:
            job.status = 'failed'
            job.error_message = str(e)
            db.session.commit()

@celery_app.task(bind=True, max_retries=3)
def download_thumbnail_task(self, video_id: str, remote_url: str):
    """
    Downloads thumbnail and updates DB to point to local path.
    """
    try:
        local_path = download_thumbnail(video_id, remote_url)
        if local_path:
            video = VideoRepository.get_by_id(video_id)
            if video:
                video.thumbnail_url = local_path
                db.session.commit()
    except Exception as e:
        logger.exception(f"Failed to download thumbnail for video {video_id}")

class CancelledError(Exception):
    pass

class DownloadProgressHook:
    def __init__(self, job_id, history_id):
        self.job_id = job_id
        self.history_id = history_id
        self.last_update_time = 0
        self.last_percent = -1

    def __call__(self, d):
        import time
        from app import db
        from app.models.queue import ProcessingQueue
        from app.models.history import DownloadHistory
        
        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            percent = 0
            if total > 0:
                percent = int(downloaded * 100 / total)
            
            speed = d.get('speed')
            eta = d.get('eta')
            
            now = time.time()
            if now - self.last_update_time >= 1.0 or percent != self.last_percent or percent == 100:
                self.last_update_time = now
                self.last_percent = percent
                
                speed_str = "0 B/s"
                if speed:
                    if speed > 1024 * 1024:
                        speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                    elif speed > 1024:
                        speed_str = f"{speed / 1024:.1f} KB/s"
                    else:
                        speed_str = f"{speed} B/s"
                        
                eta_str = "Unknown"
                if eta:
                    mins = int(eta) // 60
                    secs = int(eta) % 60
                    eta_str = f"{mins:02d}:{secs:02d}"
                
                try:
                    # Query inside current session
                    job = db.session.query(ProcessingQueue).get(self.job_id)
                    if job:
                        if job.status == 'cancelled':
                            raise CancelledError("Download cancelled")
                        payload = job.payload or {}
                        payload.update({
                            'progress_percent': percent,
                            'speed': speed_str,
                            'eta': eta_str,
                            'downloaded_bytes': downloaded,
                            'total_bytes': total
                        })
                        job.payload = payload
                        
                    dl = db.session.query(DownloadHistory).get(self.history_id)
                    if dl:
                        if dl.status == 'cancelled':
                            raise CancelledError("Download cancelled")
                        dl.progress_percent = percent
                        dl.status = 'downloading'
                        
                    db.session.commit()
                except CancelledError:
                    raise
                except Exception as e:
                    db.session.rollback()
                    logger.warning(f"Failed to update download progress in DB: {str(e)}")

def cleanup_temp_files(download_dir, history_id):
    import os
    try:
        if os.path.exists(download_dir):
            prefix = f"temp_{history_id}_"
            for filename in os.listdir(download_dir):
                if filename.startswith(prefix):
                    file_path = os.path.join(download_dir, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
    except Exception as e:
        logger.warning(f"Failed to clean up temp files for history {history_id}: {str(e)}")

def parse_rate_limit(rate_limit_str):
    if not rate_limit_str:
        return None
    if isinstance(rate_limit_str, (int, float)):
        return float(rate_limit_str)
    
    rate_limit_str = str(rate_limit_str).strip().upper()
    if not rate_limit_str or rate_limit_str in ['NONE', 'NULL', 'UNDEFINED', '']:
        return None
        
    import re
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMG])?B?$', rate_limit_str)
    if not match:
        try:
            return float(rate_limit_str)
        except ValueError:
            return None
            
    val = float(match.group(1))
    suffix = match.group(2)
    
    if suffix == 'K':
        return val * 1024
    elif suffix == 'M':
        return val * 1024 * 1024
    elif suffix == 'G':
        return val * 1024 * 1024 * 1024
        
    return val

@celery_app.task(bind=True, max_retries=1)
def download_video_task(self, job_id: str, history_id: int):
    import os
    import shutil
    import requests
    import yt_dlp
    from app import db
    from app.models.queue import ProcessingQueue
    from app.models.history import DownloadHistory
    from app.models.video import Video
    from app.repositories.video_repository import VideoRepository
    from flask import current_app
    from yt_dlp.utils import sanitize_filename
    
    logger.info(f"Starting download task for job {job_id}, history {history_id}")
    
    job = db.session.query(ProcessingQueue).get(job_id)
    history = db.session.query(DownloadHistory).get(history_id)
    
    if not job or not history:
        logger.error("Job or history record not found")
        return
        
    job.status = 'processing'
    history.status = 'downloading'
    db.session.commit()
    
    payload = job.payload or {}
    url = payload.get('url')
    video_id = history.video_id
    download_type = history.download_type
    quality = history.quality
    format_option = payload.get('format', 'mp4')
    
    download_dir = current_app.config.get('DOWNLOAD_DIR')
    if not download_dir:
        download_dir = os.path.join(os.getcwd(), 'downloads')
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # Check if video metadata exists
        video = db.session.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise Exception(f"Video with ID {video_id} not found in database. Downloader rejects downloading untracked videos.")

            
        from app.models.settings import UserSettings
        settings = db.session.query(UserSettings).get(1)
        
        proxy = settings.ytdlp_proxy if settings else None
        cookies_file = settings.cookies_file_path if settings else None
        client_name = settings.ytdlp_player_client if settings else 'ios'
        rate_limit = settings.ytdlp_rate_limit if settings else None
        
        outtmpl = os.path.join(download_dir, f"temp_{history_id}_%(title)s [%(id)s].%(ext)s")
        ffmpeg_available = shutil.which('ffmpeg') is not None
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'outtmpl': outtmpl,
        }
        
        if proxy:
            ydl_opts['proxy'] = proxy
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            
        ydl_opts['extractor_args'] = {
            'youtube': {
                'player_client': [client_name, 'default']
            }
        }
        
        if rate_limit:
            parsed_limit = parse_rate_limit(rate_limit)
            if parsed_limit:
                ydl_opts['ratelimit'] = parsed_limit
            
        progress_tracker = DownloadProgressHook(job_id, history_id)
        ydl_opts['progress_hooks'] = [progress_tracker]
        
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
                
        elif download_type == 'subtitle':
            raise Exception("Subtitle downloads are no longer supported.")
            
        elif download_type == 'thumbnail':
            thumb_url = video.thumbnail_url if video else f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            title = video.title if video else f"thumbnail_{video_id}"
            safe_title = sanitize_filename(title)
            ext = thumb_url.split('.')[-1].split('?')[0]
            if ext not in ['jpg', 'png', 'webp', 'jpeg']:
                ext = 'jpg'
            filename = f"temp_{history_id}_{safe_title} [{video_id}].{ext}"
            file_path = os.path.join(download_dir, filename)
            
            logger.info(f"Downloading thumbnail from {thumb_url} to {file_path}")
            res = requests.get(thumb_url, stream=True, timeout=15)
            res.raise_for_status()
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(res.raw, f)
                
            history.file_path = file_path
            history.file_size_bytes = os.path.getsize(file_path)
            history.status = 'complete'
            history.progress_percent = 100
            
            job.status = 'complete'
            db.session.commit()
            return
            
        else:
            raise Exception(f"Unsupported download type: {download_type}")
            
        # Log yt-dlp execution options
        logger.info(
            f"Executing yt-dlp download:\n"
            f"  URL: {url}\n"
            f"  Options: {ydl_opts}\n"
            f"  FFmpeg Available: {ffmpeg_available}"
        )

            
        logger.info(f"Running yt-dlp download for url {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            
            base_name, _ = os.path.splitext(filename)
            final_ext = format_option if download_type in ['video', 'audio'] else 'mp4'
            if download_type == 'audio' and ffmpeg_available:
                final_ext = format_option
            
            final_path = filename
            if not os.path.exists(final_path):
                for ext in [final_ext, 'mp4', 'mkv', 'webm', 'mp3', 'm4a', 'wav', 'vtt', 'srt']:
                    test_path = f"{base_name}.{ext}"
                    if os.path.exists(test_path):
                        final_path = test_path
                        break
            

            
            if not os.path.exists(final_path) or os.path.getsize(final_path) == 0:
                raise Exception(f"Downloaded file not found or is empty: {final_path}")
                
            history.file_path = final_path
            history.file_size_bytes = os.path.getsize(final_path)
            history.status = 'complete'
            history.progress_percent = 100
            
            job.status = 'complete'
            db.session.commit()
            logger.info(f"Download successfully completed. File path: {final_path}")
            
    except CancelledError:
        logger.info(f"Download job {job_id} was cancelled by user")
        cleanup_temp_files(download_dir, history_id)
        db.session.rollback()
        history = db.session.query(DownloadHistory).get(history_id)
        job = db.session.query(ProcessingQueue).get(job_id)
        if history:
            history.status = 'cancelled'
        if job:
            job.status = 'cancelled'
        db.session.commit()
        
    except Exception as e:
        logger.exception(f"Download task failed for job {job_id}")
        db.session.rollback()
        cleanup_temp_files(download_dir, history_id)
        
        err_msg = str(e)
        if download_type == 'subtitle':
            err_lower = err_msg.lower()
            if 'subtitle' in err_lower or 'caption' in err_lower or 'not available' in err_lower or 'no video formats' in err_lower or 'file not found' in err_lower or 'empty' in err_lower:
                err_msg = f"No subtitles or captions are available for this video in language '{quality}'."
                
        job = db.session.query(ProcessingQueue).get(job_id)
        history = db.session.query(DownloadHistory).get(history_id)
        if history:
            history.status = 'failed'
            history.error_message = err_msg
        if job:
            job.status = 'failed'
            job.error_message = err_msg
        db.session.commit()


