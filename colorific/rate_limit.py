from dataclasses import dataclass

from aiohttp.web import Request
from aioredis import Redis


class RateLimitExceeded(Exception):
    """
    Raises when a rate limit is exceeded.
    """


@dataclass
class RateLimit:
    name: str
    time_interval: int
    limit: int
    error: str

    async def ensure(self, request: Request) -> None:
        """
        This method relies on X-Real-IP header as a client identifier.
        This header has to be set by reverse proxy server.

        Raises
        ------
        RateLimitExceeded
            If the limit for specific IP is exceeded.
        """
        if "X-Real-IP" not in request.headers:
            return None

        redis: Redis = request.app["redis"]
        ip: str = request.headers["X-Real-IP"]

        key = f"{ip}:{self.name}:{self.time_interval}"
        value = int(await redis.incr(key))
        if value == 1:
            await redis.expire(key, self.time_interval)

        if value > self.limit:
            ttl = int(await redis.ttl(key))
            raise RateLimitExceeded(self.error, ttl)
