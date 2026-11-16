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
            from app.models.video import Video
            from app import db
            
            # Reconcile counts dynamically from crawled videos in DB using a single query
            row = db.session.query(
                db.func.count(Video.id),
                db.func.sum(Video.view_count),
                db.func.min(Video.upload_date)
            ).filter(Video.channel_id == channel_id).first()
            
            if row:
                db_video_count = row[0] or 0
                db_view_count = row[1] or 0
                db_join_date = row[2]
                
                # Sync in-memory attributes without triggering DB write on read requests
                if not channel.video_count or db_video_count > channel.video_count:
                    channel.video_count = db_video_count
                if db_view_count > 0 and (not channel.view_count or db_view_count > channel.view_count):
                    channel.view_count = db_view_count
                if not channel.join_date and db_join_date:
                    channel.join_date = db_join_date
                    
        return channel
        
    @staticmethod
    def get_channels(page: int = 1, per_page: int = 20, sort_by: str = 'name'):
        items, total = ChannelRepository.get_all(page, per_page, sort_by)
        if not items:
            return items, total
            
        from app.models.video import Video
        from app import db
        
        # Eliminate N+1 query problem by fetching aggregated stats in a single grouped query
        channel_ids = [c.id for c in items]
        stats = db.session.query(
            Video.channel_id,
            db.func.count(Video.id),
            db.func.sum(Video.view_count),
            db.func.min(Video.upload_date)
        ).filter(Video.channel_id.in_(channel_ids)).group_by(Video.channel_id).all()
        
        stats_map = {row[0]: (row[1] or 0, row[2] or 0, row[3]) for row in stats}
        
        for channel in items:
            if channel.id in stats_map:
                db_video_count, db_view_count, db_join_date = stats_map[channel.id]
                if not channel.video_count or db_video_count > channel.video_count:
                    channel.video_count = db_video_count
                if db_view_count > 0 and (not channel.view_count or db_view_count > channel.view_count):
                    channel.view_count = db_view_count
                if not channel.join_date and db_join_date:
                    channel.join_date = db_join_date
                    
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
