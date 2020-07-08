"""
Smoke test for Redis setup.
"""


async def test_redis_available(client):
    assert "redis" in client.server.app
    await client.server.app["redis"].set("_foo", 42, expire=60)
    value = await client.server.app["redis"].get("_foo")
    assert value == b"42"
    await client.server.app["redis"].flushdb()
    value = await client.server.app["redis"].get("_foo")
    assert value is None
