from app.jobs.celery_app import celery_app
from app.extraction.ytdlp_client import YtdlpClient
from app.repositories.channel_repository import ChannelRepository
from app.models.queue import ProcessingQueue
from app import db
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def extract_channel_metadata_task(self, job_id: str, url: str):
    job = db.session.query(ProcessingQueue).get(job_id)
    if not job:
        return
        
    job.status = 'processing'
    db.session.commit()
    
    try:
        client = YtdlpClient()
        data = client.extract_channel_metadata(url)
        
        channel_id = data.get('id')
        if not channel_id:
            raise Exception("No channel ID found in yt-dlp output")
            
        existing = ChannelRepository.get_by_id(channel_id)
        data['last_crawled_at'] = datetime.now(timezone.utc)
        
        if existing:
            # Merge logic: protect existing statistics from being overwritten by 0 or null
            if not data.get('video_count') or data['video_count'] == 0:
                data['video_count'] = existing.video_count
            if not data.get('view_count') or data['view_count'] == 0:
                data['view_count'] = existing.view_count
            if not data.get('join_date'):
                data['join_date'] = existing.join_date

            ChannelRepository.update(existing, data)
        else:
            ChannelRepository.create(data)
            
        job.status = 'complete'
        job.target_id = channel_id 
        db.session.commit()
        
    except Exception as e:
        logger.exception(f"Failed to extract channel metadata for {url}")
        job.status = 'failed'
        job.error_message = str(e)
        db.session.commit()
