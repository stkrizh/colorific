from aiohttp.web import Request
from aioredis import Redis


async def is_exceeded(
    request: Request, name: str, time_interval: int, limit: int
) -> bool:
    """
    This method relies on X-Real-IP header as a client identifier.
    This header has to be set by reverse proxy server.
    """
    if "X-Real-IP" not in request.headers:
        return False
    redis: Redis = request.app["redis"]
    ip: str = request.headers["X-Real-IP"]
    return await _is_exceeded(redis, ip, name, time_interval, limit)


async def _is_exceeded(
    redis: Redis, ip: str, name: str, time_interval: int, limit: int
) -> bool:
    """
    Check limit `name` for `ip`. Return False if the limit is exceeded.
    """
    key = f"{ip}:{name}:{time_interval}"
    value = int(await redis.incr(key))
    if value == 1:
        await redis.expire(key, time_interval)
    return value > limit
