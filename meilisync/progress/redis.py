import redis.asyncio as redis

from meilisync.enums import ProgressType
from meilisync.progress import Progress


class Redis(Progress):
    type = ProgressType.redis

    def __init__(
        self,
        dsn: str = "redis://localhost:6379/0",
        key: str = "meilisync:progress",
    ):
        super().__init__(dsn=dsn, key=key)
        self.key = key
        self.redis = redis.from_url(dsn, decode_responses=True)

    async def set(self, **kwargs):
        await self.redis.hmset(self.key, kwargs)

    async def get(self):
        return await self.redis.hgetall(self.key)
