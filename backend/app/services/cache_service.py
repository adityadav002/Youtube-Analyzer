import json
import logging
from typing import Any, Optional
import redis
from app.config import config_by_name
import os

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        env = os.environ.get('FLASK_ENV', 'production')
        redis_url = config_by_name[env].REDIS_URL
        # Using db 2 for cache
        cache_url = redis_url.rsplit('/', 1)[0] + '/2'
        self.redis = redis.from_url(cache_url)

    def get(self, key: str) -> Optional[Any]:
        try:
            val = self.redis.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: Any, timeout_seconds: int = 3600) -> bool:
        try:
            self.redis.setex(key, timeout_seconds, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

cache_service = CacheService()
