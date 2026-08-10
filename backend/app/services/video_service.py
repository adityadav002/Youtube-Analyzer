import uuid
from typing import Tuple, List, Optional
from app import db
from app.models.queue import ProcessingQueue
from app.repositories.video_repository import VideoRepository
from app.models.video import Video
from app.utils.task_dispatcher import dispatch_task

class VideoService:
    @staticmethod
    def get_videos(page: int = 1, per_page: int = 20, sort_by: str = 'upload_date', sort_order: str = 'desc', channel_id: str = None, search_query: str = None, is_short: bool = None, is_live: bool = None) -> Tuple[List[Video], int]:
        return VideoRepository.get_all(page, per_page, sort_by, sort_order, channel_id, search_query, is_short, is_live)

    @staticmethod
    def get_video(video_id: str) -> Optional[Video]:
        return VideoRepository.get_by_id(video_id)

    @staticmethod
    def crawl_channel(channel_id: str, start_index: int = 1, limit: int = 20, refresh_mode: bool = False) -> str:
        """
        Triggers a background task to crawl a channel and save basic video stubs.
        """
        from app.jobs.video_jobs import crawl_channel_videos_task
        
        job_id = str(uuid.uuid4())
        job = ProcessingQueue(
            id=job_id,
            job_type='crawl_channel',
            target_id=channel_id,
            status='queued',
            payload={
                'start_index': start_index,
                'limit': limit,
                'refresh_mode': refresh_mode
            }
        )
        db.session.add(job)
        db.session.commit()
        
        dispatch_task(crawl_channel_videos_task, job_id, channel_id)
        return job_id

    @staticmethod
    def extract_metadata(video_id: str) -> str:
        """
        Triggers a background task to extract deep metadata for a single video.
        """
        from app.jobs.video_jobs import extract_video_metadata_task
        
        job_id = str(uuid.uuid4())
        job = ProcessingQueue(
            id=job_id,
            job_type='extract_video',
            target_id=video_id,
            status='queued'
        )
        db.session.add(job)
        db.session.commit()
        
        dispatch_task(extract_video_metadata_task, job_id, video_id)
        return job_id

    @staticmethod
    def delete_video(video_id: str) -> bool:
        video = VideoRepository.get_by_id(video_id)
        if video:
            VideoRepository.delete(video)
            db.session.commit()
            return True
        return False
