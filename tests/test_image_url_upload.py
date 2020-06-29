import os
from asyncio import TimeoutError
from io import BytesIO
from typing import Union
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientConnectorError, ClientResponseError
from tenacity import RetryError

from colorific.settings import config
from colorific.views import IMAGE_INVALID_TYPE_ERROR, IMAGE_TOO_LARGE_ERROR

VALID_URL = "https://example.com/image.jpg"


class StreamReaderMock:
    def __init__(self, data: Union[int, bytes]):
        if isinstance(data, int):
            self.buffer = BytesIO(os.urandom(data))
        else:
            self.buffer = BytesIO(data)

    async def iter_chunked(self, chunk_size: int):
        while True:
            chunk = self.buffer.read(chunk_size)
            if not chunk:
                return
            yield chunk


class ResponseMock:
    def __init__(self, data: Union[int, bytes] = b""):
        self.content = StreamReaderMock(data)

    async def __aenter__(self, *args, **kwargs):
        return self

    async def __aexit__(self, *args, **kwargs):
        ...


async def test_correct_request(client, get_image_data):
    image_data = get_image_data()
    with patch(
        "colorific.views.ColorExtractionView.download_image_by_url",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = image_data
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 200
        response_json = await response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == 1
        mock.assert_awaited_once()


@pytest.mark.parametrize(
    "url",
    [42, "", "    ", "foo", "examplecom/image.jpg", "htt://example.com/image.jpg"],
)
async def test_invalid_url(client, url):
    response = await client.put("/image", json={"url": url})
    assert response.status == 400
    response_json = await response.json()
    assert "url" in response_json


async def test_retry_error(client):
    def side_effect(*args, **kwargs):
        raise RetryError(None)

    with patch(
        "colorific.views.ColorExtractionView.download_image_by_url",
        new_callable=AsyncMock,
    ) as mock:
        mock.side_effect = side_effect
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["url"] == "The requested resource is not available."


async def test_response_status_error(client):
    def side_effect(*args, **kwargs):
        raise ClientResponseError(None, None)

    with patch("aiohttp.client.ClientSession.get", return_value=ResponseMock()) as mock:
        mock.return_value.raise_for_status = Mock(side_effect=side_effect)
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["url"] == "The requested resource is not available."


async def test_network_error(client):
    def side_effect(*args, **kwargs):
        raise ClientConnectorError(Mock(), Mock())

    with patch("aiohttp.client.ClientSession.get", side_effect=side_effect):
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["url"] == "The requested resource is not available."


async def test_timeout_error(client):
    def side_effect(*args, **kwargs):
        raise TimeoutError()

    with patch("aiohttp.client.ClientSession.get", side_effect=side_effect):
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["url"] == "The requested resource is not available."


@pytest.mark.parametrize(
    "content_type",
    [
        None,
        "",
        "application/json",
        "text/html",
        " image/jpeg   ",
        "image/jpg",
        "image/PNG",
    ],
)
async def test_invalid_content_type(client, content_type):
    with patch("aiohttp.client.ClientSession.get", return_value=ResponseMock()) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = content_type
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["image"] == IMAGE_INVALID_TYPE_ERROR


@pytest.mark.parametrize(
    "content_length, expected_err_key",
    [
        (None, "content_length"),
        ("", "content_length"),
        (config.colorific.image_max_size_bytes + 1, "image"),
    ],
)
async def test_invalid_content_length(client, content_length, expected_err_key):
    with patch("aiohttp.client.ClientSession.get", return_value=ResponseMock()) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = content_length
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert expected_err_key in response_json


async def test_max_image_size_exceeded(client):
    with patch(
        "aiohttp.client.ClientSession.get",
        return_value=ResponseMock(config.colorific.image_max_size_bytes + 1),
    ) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = config.colorific.image_max_size_bytes
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["image"] == IMAGE_TOO_LARGE_ERROR


async def test_max_image_size_limit(client):
    with patch(
        "aiohttp.client.ClientSession.get",
        return_value=ResponseMock(config.colorific.image_max_size_bytes),
    ) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = 100
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["image"] == ["Invalid image format."]


async def test_invalid_image_format(client, get_image_data):
    image_data = get_image_data()
    image_data = os.urandom(100) + image_data
    with patch(
        "aiohttp.client.ClientSession.get", return_value=ResponseMock(image_data),
    ) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = len(image_data)
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert response_json["image"] == ["Invalid image format."]


@pytest.mark.parametrize(
    "width, height",
    [
        (config.colorific.image_min_width - 1, config.colorific.image_min_height - 1),
        (config.colorific.image_min_width - 1, 500),
        (500, config.colorific.image_min_height - 1),
        (config.colorific.image_max_width + 1, config.colorific.image_max_height + 1),
        (config.colorific.image_max_width + 1, 500),
        (500, config.colorific.image_max_height + 1),
    ],
)
async def test_invalid_image_dimensions(client, get_image_data, width, height):
    image_data = get_image_data(size=(width, height))
    with patch(
        "aiohttp.client.ClientSession.get", return_value=ResponseMock(image_data),
    ) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = len(image_data)
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 400
        response_json = await response.json()
        assert "image" in response_json


async def test_valid_four_color_image(client, get_four_color_image):
    image = get_four_color_image("RGB")
    with BytesIO() as buffer:
        image.save(buffer, "JPEG")
        buffer.seek(0)
        image_data = buffer.read()
    image.close()

    with patch(
        "aiohttp.client.ClientSession.get", return_value=ResponseMock(image_data),
    ) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = len(image_data)
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 200
        response_json = await response.json()
        assert isinstance(response_json, list)
        assert len(response_json) > 2


@pytest.mark.parametrize(
    "image_format, width, height",
    [
        ("JPEG", config.colorific.image_min_width, config.colorific.image_min_height),
        ("PNG", config.colorific.image_min_width, 500),
        ("JPEG", 500, config.colorific.image_min_height),
        ("PNG", config.colorific.image_max_width, config.colorific.image_max_height),
        ("JPEG", config.colorific.image_max_width, 500),
        ("PNG", 500, config.colorific.image_max_height),
    ],
)
async def test_valid_one_color_image(
    client, get_image_data, image_format, width, height
):
    image_data = get_image_data(size=(width, height), image_format=image_format)
    with patch(
        "aiohttp.client.ClientSession.get", return_value=ResponseMock(image_data),
    ) as mock:
        mock.return_value.raise_for_status = Mock()
        mock.return_value.content_type = "image/jpeg"
        mock.return_value.content_length = len(image_data)
        response = await client.put("/image", json={"url": VALID_URL})
        assert response.status == 200
        response_json = await response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == 1
