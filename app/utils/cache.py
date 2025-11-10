# app/utils/cache.py
import json
from typing import Optional, Any
import redis.asyncio as redis


class CacheManager:
    """Async Redis cache manager using redis.asyncio."""

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, decode_responses: bool = True):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=decode_responses)

    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self.redis.get(key)
            if not value:
                return None
            return json.loads(value)
        except Exception:
            return None

    async def set(self, key: str, value: Any, ttl: int = 86400) -> bool:
        try:
            payload = json.dumps(value)
            await self.redis.setex(key, ttl, payload)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False

    async def close(self):
        try:
            await self.redis.close()
        except Exception:
            pass
