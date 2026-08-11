import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from sqlalchemy import or_
from app import db
from app.services.youtube_api_service import YouTubeApiService
from app.models.video import Video
from app.models.channel import Channel
from app.models.transcript import Transcript
from app.repositories.search_repository import SearchRepository

logger = logging.getLogger(__name__)

def format_timestamp(seconds: float) -> str:
    s = int(seconds)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"

def highlight_match(text: str, query: str) -> str:
    # Wrap case-insensitive matches in square brackets per spec
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return pattern.sub(lambda m: f"[{m.group(0)}]", text)

class SearchService:
    @staticmethod
    def search_youtube(
        query: str, 
        search_type: str = 'video', 
        max_results: int = 20, 
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Searches YouTube via yt-dlp. Results are cached in the search_history table for 1 hour.
        """
        # Truncate query to 200 characters per spec
        query_truncated = query[:200]
        
        # Check cache if refresh is not requested
        if not refresh:
            cached_record = None
            try:
                cached_record = SearchRepository.get_cached_query(query_truncated, search_type)
            except Exception as db_err:
                logger.error(f"Database error during search cache lookup for query '{query_truncated}': {db_err}")
                raise
                
            if cached_record and cached_record.expires_at > datetime.utcnow():
                try:
                    results = json.loads(cached_record.results_json) if cached_record.results_json else []
                    if not isinstance(results, list):
                        results = []
                    
                    logger.info(f"Serving search results from cache for: {query_truncated} (type: {search_type})")
                    
                    # Check which videos are already in our library to set "in_library" flag
                    if search_type == 'video':
                        video_ids = [r['video_id'] for r in results if 'video_id' in r]
                        if video_ids:
                            existing = db.session.query(Video.id).filter(Video.id.in_(video_ids)).all()
                            existing_ids = {v[0] for v in existing}
                            for r in results:
                                r['in_library'] = r['video_id'] in existing_ids
                    
                    return {
                        'query': query_truncated,
                        'type': search_type,
                        'cached': True,
                        'cached_at': cached_record.updated_at.isoformat() if cached_record.updated_at else cached_record.created_at.isoformat(),
                        'results': results
                    }
                except (json.JSONDecodeError, TypeError) as json_err:
                    logger.warning(f"Malformed or invalid cached JSON for query '{query_truncated}': {json_err}. Treating as cache miss.")
                    # Let it fall through to run fresh yt-dlp search

        # Search via YouTube Data API
        logger.info(f"Searching YouTube via YouTube Data API for: {query_truncated} (type: {search_type})")
        api_service = YouTubeApiService()
        results = api_service.search_youtube(query_truncated, search_type, max_results)
        
        # Save search results to cache
        try:
            SearchRepository.save_query_cache(query_truncated, search_type, len(results), results)
        except Exception as db_err:
            logger.error(f"Database error during search cache save for query '{query_truncated}': {db_err}")
            raise
        
        # Populate in_library status for video results
        if search_type == 'video':
            video_ids = [r['video_id'] for r in results if 'video_id' in r]
            if video_ids:
                existing = db.session.query(Video.id).filter(Video.id.in_(video_ids)).all()
                existing_ids = {v[0] for v in existing}
                for r in results:
                    r['in_library'] = r['video_id'] in existing_ids

        return {
            'query': query_truncated,
            'type': search_type,
            'cached': False,
            'results': results
        }


    @staticmethod
    def search_internal(
        query: str,
        search_type: str = 'video',
        channel_id: Optional[str] = None,
        has_transcript: Optional[str] = None,
        is_short: Optional[str] = None,
        upload_after: Optional[str] = None,
        upload_before: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Searches the local database (videos, channels, transcripts).
        """
        if search_type == 'video':
            db_query = db.session.query(Video)
            
            # Text matching on title/description
            search_term = f"%{query}%"
            db_query = db_query.filter(
                or_(
                    Video.title.ilike(search_term),
                    Video.description.ilike(search_term)
                )
            )
            
            # Apply filters
            if channel_id:
                db_query = db_query.filter(Video.channel_id == channel_id)
                
            if has_transcript == 'yes':
                db_query = db_query.filter(Video.has_transcript == True)
            elif has_transcript == 'no':
                db_query = db_query.filter(Video.has_transcript == False)
                
            if is_short == 'yes':
                db_query = db_query.filter(Video.is_short == True)
            elif is_short == 'no':
                db_query = db_query.filter(Video.is_short == False)
                
            if upload_after:
                try:
                    dt = datetime.strptime(upload_after, '%Y-%m-%d')
                    db_query = db_query.filter(Video.upload_date >= dt)
                except ValueError:
                    pass
                    
            if upload_before:
                try:
                    dt = datetime.strptime(upload_before, '%Y-%m-%d')
                    db_query = db_query.filter(Video.upload_date <= dt)
                except ValueError:
                    pass
            
            # Order by upload date desc
            from sqlalchemy.sql.functions import coalesce
            db_query = db_query.order_by(coalesce(Video.upload_date, Video.created_at).desc())
            
            total = db_query.count()
            items = db_query.offset((page - 1) * per_page).limit(per_page).all()
            
            from app.schemas.video_schema import VideoSchema
            serialized = VideoSchema(many=True).dump(items)
            
            return {
                'items': serialized,
                'total': total,
                'page': page,
                'per_page': per_page
            }
            
        elif search_type == 'channel':
            db_query = db.session.query(Channel)
            search_term = f"%{query}%"
            db_query = db_query.filter(
                or_(
                    Channel.display_name.ilike(search_term),
                    Channel.handle.ilike(search_term),
                    Channel.description.ilike(search_term)
                )
            )

            
            total = db_query.count()
            items = db_query.offset((page - 1) * per_page).limit(per_page).all()
            
            from app.schemas.channel_schema import ChannelSchema
            serialized = ChannelSchema(many=True).dump(items)
            
            return {
                'items': serialized,
                'total': total,
                'page': page,
                'per_page': per_page
            }
            
        elif search_type == 'transcript':
            # Query transcripts matching full_text using FULLTEXT index match, fall back to ilike
            try:
                transcripts = db.session.query(Transcript).filter(
                    Transcript.full_text.match(query)
                ).all()
            except Exception as e:
                db.session.rollback()
                logger.warning(f"FULLTEXT MATCH failed, falling back to ILIKE: {e}")
                search_term = f"%{query}%"
                transcripts = db.session.query(Transcript).filter(
                    Transcript.full_text.ilike(search_term)
                ).all()
                
            results = []
            for transcript in transcripts:
                video = transcript.video
                if not video:
                    continue
                
                # Check channel_id filter if applied
                if channel_id and video.channel_id != channel_id:
                    continue
                    
                channel = video.channel
                channel_name = channel.display_name if channel else "YouTube Channel"
                
                # Search inside segments to find exact matches
                segments = transcript.segments or []
                for s in segments:
                    text = s.get('text', '')
                    if query.lower() in text.lower():
                        # Determine start time
                        start_time = s.get('start', s.get('start_seconds', 0.0))
                        
                        results.append({
                            'video_id': video.id,
                            'video_title': video.title,
                            'channel_name': channel_name,
                            'thumbnail_url': video.thumbnail_url,
                            'duration': video.duration,
                            'timestamp': start_time,
                            'timestamp_formatted': format_timestamp(start_time),
                            'excerpt': highlight_match(text, query)
                        })
                        
            # Paginate in-memory results list
            total = len(results)
            items = results[(page - 1) * per_page : page * per_page]
            
            return {
                'items': items,
                'total': total,
                'page': page,
                'per_page': per_page
            }
            
        return {
            'items': [],
            'total': 0,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def get_search_history(limit: int = 20) -> List[Dict[str, Any]]:
        """
        Retrieves search history entries formatted for display in the collapse panel.
        """
        records = SearchRepository.get_recent_searches(limit)
        results = []
        now = datetime.utcnow()
        for r in records:
            results.append({
                'id': r.id,
                'query': r.query,
                'search_type': r.search_type,
                'result_count': r.result_count,
                'searched_at': r.created_at.isoformat() if r.created_at else None,
                'expires_at': r.expires_at.isoformat() if r.expires_at else None,
                'is_expired': r.expires_at < now if r.expires_at else True
            })
        return results
