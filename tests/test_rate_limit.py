import asyncio
from collections import Counter
from itertools import cycle, islice
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
