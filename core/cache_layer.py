"""
Cache layer using Redis for fast memory and metadata retrieval.
"""
import json
from typing import Optional, Dict, Any

from core.config import get_config

try:
    from redis import asyncio as aioredis
except ImportError:
    aioredis = None


class CacheLayer:
    def __init__(self, redis_url: Optional[str] = None):
        cfg = get_config()
        self.url = redis_url or cfg.redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def init(self):
        if aioredis is None:
            raise RuntimeError("aioredis not installed")
        self.redis = await aioredis.from_url(self.url, decode_responses=True)

    async def get_conversation(self, resource: str, thread: str) -> Optional[Dict[str, Any]]:
        key = f"conv:{resource}:{thread}"
        if self.redis is None:
            return None
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set_conversation(self, resource: str, thread: str, data: Dict[str, Any]):
        if self.redis is None:
            return
        key = f"conv:{resource}:{thread}"
        await self.redis.setex(key, 86400, json.dumps(data))  # 24h TTL

    async def invalidate(self, pattern: str = "*"):
        if self.redis is None:
            return
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
