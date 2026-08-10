import logging
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy import or_
from app import db
from app.models.video import Video

logger = logging.getLogger(__name__)

class VideoRepository:
    @staticmethod
    def resolve_classification(
        is_short: bool,
        is_live: bool,
        live_status: str,
        duration: int
    ) -> Tuple[bool, bool, str]:
        """
        Applies classification logic to enforce database invariants:
        - LIVE: is_live=True, is_short=False
        - SHORT: is_short=True, is_live=False
        - NORMAL: is_short=False, is_live=False
        - Never allows is_short=True and is_live=True.
        """
        # Determine is_live first (highest priority)
        resolved_is_live = False
        if is_live or live_status in ['is_live', 'was_live', 'post_live']:
            resolved_is_live = True
            
        # Determine is_short (second priority)
        resolved_is_short = False
        if not resolved_is_live:
            if is_short:
                resolved_is_short = True
            # Fallback signal: duration > 0 and duration < 60 seconds
            elif duration and 0 < duration < 60:
                resolved_is_short = True
                
        # Resolve live_status
        resolved_live_status = live_status
        if resolved_is_live:
            if not live_status or live_status == 'not_live':
                resolved_live_status = 'was_live' # Default to was_live if not specified
        else:
            resolved_live_status = 'not_live'
            
        return resolved_is_short, resolved_is_live, resolved_live_status

    @staticmethod
    def get_by_id(video_id: str) -> Optional[Video]:
        return db.session.query(Video).filter(Video.id == video_id).first()

    @staticmethod
    def get_all(
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'upload_date',
        sort_order: str = 'desc',
        channel_id: Optional[str] = None,
        search_query: Optional[str] = None,
        is_short: Optional[bool] = None,
        is_live: Optional[bool] = None
    ) -> Tuple[List[Video], int]:
        
        query = db.session.query(Video)
        
        # Filtering
        if channel_id:
            query = query.filter(Video.channel_id == channel_id)
            
        if is_short is not None:
            query = query.filter(Video.is_short == is_short)
            
        if is_live is not None:
            query = query.filter(Video.is_live == is_live)
            
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Video.title.ilike(search_term),
                    Video.description.ilike(search_term)
                )
            )
            
        # Sorting
        if sort_by == 'upload_date':
            from sqlalchemy.sql.functions import coalesce
            sort_column = coalesce(Video.upload_date, Video.created_at)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        elif hasattr(Video, sort_by):
            column = getattr(Video, sort_by)
            if sort_order == 'desc':
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            from sqlalchemy.sql.functions import coalesce
            query = query.order_by(coalesce(Video.upload_date, Video.created_at).desc())
            
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return items, total

    @staticmethod
    def create(data: Dict[str, Any]) -> Video:
        data_copy = data.copy()
        is_short = data_copy.get('is_short', False)
        is_live = data_copy.get('is_live', False)
        live_status = data_copy.get('live_status', 'not_live')
        duration = data_copy.get('duration', 0)
        
        resolved_short, resolved_live, resolved_status = VideoRepository.resolve_classification(
            is_short, is_live, live_status, duration
        )
        
        data_copy['is_short'] = resolved_short
        data_copy['is_live'] = resolved_live
        data_copy['live_status'] = resolved_status
        
        # Logging classification decision
        class_name = 'NORMAL'
        if resolved_live:
            class_name = 'LIVE'
        elif resolved_short:
            class_name = 'SHORT'
        
        logger.info(
            f"Classification decision (Create) - Video ID: {data_copy.get('id')} - "
            f"Input(is_short={is_short}, is_live={is_live}, live_status={live_status}, duration={duration}) -> "
            f"Resolved({class_name}: is_short={resolved_short}, is_live={resolved_live}, live_status={resolved_status})"
        )
        
        video = Video(**data_copy)
        db.session.add(video)
        return video

    @staticmethod
    def update(video: Video, data: Dict[str, Any]) -> Video:
        data_copy = data.copy()
        
        db_is_short = video.is_short or False
        db_is_live = video.is_live or False
        db_live_status = video.live_status or 'not_live'
        db_duration = video.duration or 0
        
        in_is_short = data_copy.get('is_short', db_is_short)
        in_is_live = data_copy.get('is_live', db_is_live)
        in_live_status = data_copy.get('live_status', db_live_status)
        in_duration = data_copy.get('duration', db_duration)
        
        # Merge signals: prioritize keeping True if it was already True in DB,
        # unless incoming live_status indicates it's a livestream
        merged_is_live = db_is_live or in_is_live or (in_live_status in ['is_live', 'was_live', 'post_live'])
        merged_is_short = (db_is_short or in_is_short) and not merged_is_live
        merged_duration = in_duration or db_duration
        
        resolved_short, resolved_live, resolved_status = VideoRepository.resolve_classification(
            merged_is_short, merged_is_live, in_live_status, merged_duration
        )
        
        data_copy['is_short'] = resolved_short
        data_copy['is_live'] = resolved_live
        data_copy['live_status'] = resolved_status
        if 'duration' in data_copy:
            data_copy['duration'] = merged_duration
            
        # Logging classification decision
        class_name = 'NORMAL'
        if resolved_live:
            class_name = 'LIVE'
        elif resolved_short:
            class_name = 'SHORT'
            
        logger.info(
            f"Classification decision (Update) - Video ID: {video.id} - "
            f"Input(is_short={in_is_short}, is_live={in_is_live}, live_status={in_live_status}, duration={in_duration}) -> "
            f"Resolved({class_name}: is_short={resolved_short}, is_live={resolved_live}, live_status={resolved_status})"
        )
        
        for key, value in data_copy.items():
            if hasattr(video, key) and key not in ['id']:
                setattr(video, key, value)
        return video

    @staticmethod
    def delete(video: Video) -> None:
        db.session.delete(video)

    @staticmethod
    def bulk_create_stubs(videos_data: List[Dict[str, Any]]) -> None:
        """
        Creates video stubs in bulk. If a video already exists, we skip it or update basic info.
        For performance, we'll use DB merge or just ignore conflicts.
        """
        for data in videos_data:
            existing = VideoRepository.get_by_id(data['id'])
            if not existing:
                VideoRepository.create(data)
            else:
                if 'title' in data:
                    existing.title = data['title']
                
                db_is_short = existing.is_short or False
                db_is_live = existing.is_live or False
                db_live_status = existing.live_status or 'not_live'
                db_duration = existing.duration or 0
                
                in_is_short = data.get('is_short', False)
                in_is_live = data.get('is_live', False)
                in_live_status = data.get('live_status', 'not_live')
                in_duration = data.get('duration', 0)
                
                merged_is_live = db_is_live or in_is_live or (in_live_status in ['is_live', 'was_live', 'post_live'])
                merged_is_short = (db_is_short or in_is_short) and not merged_is_live
                merged_duration = in_duration or db_duration
                
                resolved_short, resolved_live, resolved_status = VideoRepository.resolve_classification(
                    merged_is_short, merged_is_live, in_live_status, merged_duration
                )
                
                existing.is_short = resolved_short
                existing.is_live = resolved_live
                existing.live_status = resolved_status
        db.session.commit()

    @staticmethod
    def bulk_create_stubs_tracked(videos_data: List[Dict[str, Any]]) -> Tuple[int, int]:
        inserted = 0
        updated = 0
        for data in videos_data:
            existing = VideoRepository.get_by_id(data['id'])
            if not existing:
                VideoRepository.create(data)
                inserted += 1
            else:
                if 'title' in data:
                    existing.title = data['title']
                if 'duration' in data:
                    existing.duration = data['duration']
                if 'thumbnail_url' in data:
                    existing.thumbnail_url = data['thumbnail_url']
                
                db_is_short = existing.is_short or False
                db_is_live = existing.is_live or False
                db_live_status = existing.live_status or 'not_live'
                db_duration = existing.duration or 0
                
                in_is_short = data.get('is_short', False)
                in_is_live = data.get('is_live', False)
                in_live_status = data.get('live_status', 'not_live')
                in_duration = data.get('duration', 0)
                
                merged_is_live = db_is_live or in_is_live or (in_live_status in ['is_live', 'was_live', 'post_live'])
                merged_is_short = (db_is_short or in_is_short) and not merged_is_live
                merged_duration = in_duration or db_duration
                
                resolved_short, resolved_live, resolved_status = VideoRepository.resolve_classification(
                    merged_is_short, merged_is_live, in_live_status, merged_duration
                )
                
                existing.is_short = resolved_short
                existing.is_live = resolved_live
                existing.live_status = resolved_status
                updated += 1
        db.session.commit()
        return inserted, updated
