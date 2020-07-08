import asyncio
from collections import Counter
from itertools import count, cycle, islice
from unittest.mock import AsyncMock, patch

from aiohttp.web import json_response

from colorific.settings import config
from colorific.views import ColorExtractionView


VALID_URL = "https://example.com/image.jpg"


async def test_color_extraction_mock_works(client, redis):
    with patch.object(
        ColorExtractionView, "handle_json_request", new_callable=AsyncMock
    ) as mock:
        mock.return_value = json_response({"fake": "OK"})
        response = await client.put(
            "/image", json={"url": VALID_URL}, headers={"X-Real-IP": "77.77.77.77"}
        )
        assert response.status == 200
        response_json = await response.json()
        assert response_json["fake"] == "OK"

        time_interval = config.rate_limit.color_extraction_ip_time_interval
        value = await redis.get(f"77.77.77.77:color_extraction:{time_interval}")
        assert value == b"1"


async def test_color_extraction_rate_limit_exceeded(client, redis):
    limit = config.rate_limit.color_extraction_ip_limit
    time_interval = config.rate_limit.color_extraction_ip_time_interval

    def side_effect(*args, **kwargs):
        return json_response({"fake": "OK"})

    with patch.object(
        ColorExtractionView, "handle_json_request", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = side_effect
        coros = [
            client.put(
                "/image", json={"url": VALID_URL}, headers={"X-Real-IP": "77.77.77.77"}
            )
            for _ in range(limit + 1)
        ]
        responses = await asyncio.gather(*coros)
        statuses = Counter(resp.status for resp in responses)
        assert statuses[200] == limit
        assert statuses[429] == 1

        await asyncio.sleep(time_interval)

        response = await client.put(
            "/image", json={"url": VALID_URL}, headers={"X-Real-IP": "77.77.77.77"}
        )
        assert response.status == 200


async def test_color_extraction_several_ips(client, redis):
    limit = config.rate_limit.color_extraction_ip_limit

    def side_effect(*args, **kwargs):
        return json_response({"fake": "OK"})

    with patch.object(
        ColorExtractionView, "handle_json_request", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = side_effect
        ips = ["11.11.11.11", "22.22.22.22", "33.33.33.33"]

        coros = [
            client.put("/image", json={"url": VALID_URL}, headers={"X-Real-IP": ip})
            for ip in islice(cycle(ips), (limit + 1) * len(ips))
        ]
        responses = await asyncio.gather(*coros)
        statuses = Counter(resp.status for resp in responses)
        assert statuses[200] == limit * len(ips)
        assert statuses[429] == len(ips)


async def test_image_search_several_ips(client, redis):
    limit = config.rate_limit.image_search_ip_limit

    ips = ["11.11.11.11", "22.22.22.22", "33.33.33.33"]

    coros = [
        client.get("/images?color=ff0000", headers={"X-Real-IP": ip})
        for ip in islice(cycle(ips), (limit + 1) * len(ips))
    ]
    responses = await asyncio.gather(*coros)
    statuses = Counter(resp.status for resp in responses)
    assert statuses[200] == limit * len(ips)
    assert statuses[429] == len(ips)


async def test_several_endpoints_for_one_ip(client, redis):
    limit_1 = config.rate_limit.image_search_ip_limit
    limit_2 = config.rate_limit.color_extraction_ip_limit
    ip = "77.77.77.77"

    def side_effect(*args, **kwargs):
        return json_response({"fake": "OK"})

    with patch.object(
        ColorExtractionView, "handle_json_request", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = side_effect
        coros = [
            client.get("/images?color=ff0000", headers={"X-Real-IP": ip})
            for _ in range(limit_1)
        ]
        coros += [
            client.put("/image", json={"url": VALID_URL}, headers={"X-Real-IP": ip})
            for _ in range(limit_2)
        ]
        responses = await asyncio.gather(*coros)
        statuses = Counter(resp.status for resp in responses)
        assert statuses[200] == limit_1 + limit_2

    assert len(await redis.keys("*")) == 2


async def test_color_extraction_concurrency(client, redis):
    concurrency = config.rate_limit.color_extraction_concurrency
    ips = map(str, count(start=1))

    async def side_effect(*args, **kwargs):
        await asyncio.sleep(0.5)
        return json_response({"fake": "OK"})

    with patch.object(
        ColorExtractionView, "handle_json_request", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = side_effect
        coros = [
            client.put("/image", json={"url": VALID_URL}, headers={"X-Real-IP": ip})
            for ip in islice(ips, concurrency + 2)
        ]

        responses = await asyncio.gather(*coros)
        statuses = Counter(resp.status for resp in responses)
        assert statuses[200] == concurrency
        assert statuses[503] == 2

    assert len(await redis.keys("*")) == concurrency + 2


async def test_retry_after_header(client, redis):
    limit_1 = config.rate_limit.color_extraction_ip_limit
    limit_2 = config.rate_limit.image_search_ip_limit
    ip = "77.77.77.77"

    def side_effect(*args, **kwargs):
        return json_response({"fake": "OK"})

    with patch.object(
        ColorExtractionView, "handle_json_request", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = side_effect

        coros = [
            client.put("/image", json={"url": VALID_URL}, headers={"X-Real-IP": ip})
            for _ in range(limit_1 + 2)
        ]
        coros += [
            client.get("/images?color=ffeeee", headers={"X-Real-IP": ip})
            for _ in range(limit_2 + 1)
        ]
        responses = await asyncio.gather(*coros)
        failed_responses = [resp for resp in responses if resp.status == 429]

        assert len(failed_responses) == 3
        assert all(
            resp.headers.get("Retry-After", "").isdigit() for resp in failed_responses
        )
