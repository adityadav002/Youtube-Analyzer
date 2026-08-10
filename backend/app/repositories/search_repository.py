from datetime import datetime, timedelta
from typing import List, Optional
from app import db
from app.models.history import SearchHistory

class SearchRepository:
    @staticmethod
    def get_cached_query(query: str, search_type: str) -> Optional[SearchHistory]:
        """
        Retrieves a cached search query if it exists.
        """
        return db.session.query(SearchHistory).filter(
            SearchHistory.query == query,
            SearchHistory.search_type == search_type
        ).first()

    @staticmethod
    def save_query_cache(query: str, search_type: str, result_count: int, results: list, ttl_hours: int = 1) -> SearchHistory:
        """
        Saves or updates a search query in the cache with the given TTL.
        """
        import json
        now = datetime.utcnow()
        expires = now + timedelta(hours=ttl_hours)
        
        # Check if record exists
        record = db.session.query(SearchHistory).filter(
            SearchHistory.query == query,
            SearchHistory.search_type == search_type
        ).first()
        
        if record:
            record.result_count = result_count
            record.results_json = json.dumps(results)
            record.expires_at = expires
            record.updated_at = now
        else:
            record = SearchHistory(
                query=query,
                search_type=search_type,
                result_count=result_count,
                results_json=json.dumps(results),
                expires_at=expires
            )
            db.session.add(record)
            
        db.session.commit()
        return record

    @staticmethod
    def get_recent_searches(limit: int = 20) -> List[SearchHistory]:
        """
        Retrieves the most recent search history records ordered by creation date descending.
        """
        return db.session.query(SearchHistory).order_by(SearchHistory.created_at.desc()).limit(limit).all()
