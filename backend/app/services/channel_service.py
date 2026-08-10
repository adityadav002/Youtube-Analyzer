import uuid
import logging
from app.repositories.channel_repository import ChannelRepository
from app.models.queue import ProcessingQueue
from app.utils.task_dispatcher import dispatch_task
from app import db

logger = logging.getLogger(__name__)

class ChannelService:
    @staticmethod
    def get_channel(channel_id: str):
        channel = ChannelRepository.get_by_id(channel_id)
        if channel:
            # Reconcile counts dynamically from crawled videos in DB
            from app.models.video import Video
            from app import db
            
            db_video_count = db.session.query(db.func.count(Video.id)).filter(Video.channel_id == channel_id).scalar() or 0
            db_view_count = db.session.query(db.func.sum(Video.view_count)).filter(Video.channel_id == channel_id).scalar() or 0
            db_join_date = db.session.query(db.func.min(Video.upload_date)).filter(Video.channel_id == channel_id).scalar()
            
            updated = False
            
            # Sync video count if database count is larger or if not set
            if not channel.video_count or db_video_count > channel.video_count:
                channel.video_count = db_video_count
                updated = True
                
            # If view_count is null or 0, or if the db_view_count is greater (since it grows), use db_view_count
            if db_view_count > 0 and (not channel.view_count or db_view_count > channel.view_count):
                channel.view_count = db_view_count
                updated = True
                
            # If join_date is null, use the oldest video upload date as fallback
            if not channel.join_date and db_join_date:
                channel.join_date = db_join_date
                updated = True
                
            if updated:
                db.session.commit()
                
        return channel
        
    @staticmethod
    def get_channels(page: int = 1, per_page: int = 20, sort_by: str = 'name'):
        items, total = ChannelRepository.get_all(page, per_page, sort_by)
        
        # Reconcile each channel dynamically
        from app.models.video import Video
        from app import db
        
        for channel in items:
            db_video_count = db.session.query(db.func.count(Video.id)).filter(Video.channel_id == channel.id).scalar() or 0
            db_view_count = db.session.query(db.func.sum(Video.view_count)).filter(Video.channel_id == channel.id).scalar() or 0
            db_join_date = db.session.query(db.func.min(Video.upload_date)).filter(Video.channel_id == channel.id).scalar()
            
            updated = False
            if not channel.video_count or db_video_count > channel.video_count:
                channel.video_count = db_video_count
                updated = True
            if db_view_count > 0 and (not channel.view_count or db_view_count > channel.view_count):
                channel.view_count = db_view_count
                updated = True
            if not channel.join_date and db_join_date:
                channel.join_date = db_join_date
                updated = True
            if updated:
                db.session.commit()
                
        return items, total

    @staticmethod
    def add_channel(url: str):
        """
        Parses URL, checks cache/DB, triggers Celery task.
        Returns job_id.
        """
        from app.jobs.channel_jobs import extract_channel_metadata_task
        
        job_id = str(uuid.uuid4())
        
        job = ProcessingQueue(
            id=job_id,
            job_type='extract_channel',
            target_id=url,
            status='queued'
        )
        db.session.add(job)
        db.session.commit()
        
        dispatch_task(extract_channel_metadata_task, job_id, url)
        
        return job_id

    @staticmethod
    def delete_channel(channel_id: str):
        channel = ChannelRepository.get_by_id(channel_id)
        if channel:
            ChannelRepository.delete(channel)
            return True
        return False
        
    @staticmethod
    def update_channel(channel_id: str, data: dict):
        channel = ChannelRepository.get_by_id(channel_id)
        if channel:
            return ChannelRepository.update(channel, data)
        return None
