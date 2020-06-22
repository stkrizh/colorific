from io import BytesIO

import pytest

from colorific.settings import config
from colorific.views import IMAGE_TOO_LARGE_ERROR


@pytest.fixture(scope="session")
def image_data(get_one_color_image):
    image = get_one_color_image("RGB", (255, 0, 0), (500, 500))
    with BytesIO() as buffer:
        image.save(buffer, "JPEG")
        buffer.seek(0)
        data = buffer.read()
    image.close()
    return data


@pytest.fixture(scope="session")
def get_image_data(get_one_color_image):
    def _get_image_data(color=(255, 0, 0), size=(500, 500), image_format="JPEG"):
        image = get_one_color_image("RGB", color, size)
        with BytesIO() as buffer:
            image.save(buffer, image_format)
            buffer.seek(0)
            data = buffer.read()
        image.close()
        return data

    return _get_image_data


async def test_image_without_content_type_header(client, image_data):
    response = await client.put("/image", data=image_data)
    assert response.status == 400


@pytest.mark.parametrize("content_type", ["image/JPEG", "img/PNG", "", "foo/bar"])
async def test_invalid_content_type_header(client, image_data, content_type):
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": content_type}
    )
    assert response.status == 400
    response_json = await response.json()
    assert "image" in response_json


async def test_content_length_header_exceeds_max(client, image_data):
    max_content_length = config.colorific.image_max_size_bytes
    response = await client.put(
        "/image",
        data=image_data,
        headers={
            "Content-Type": "image/jpeg",
            "Content-Length": f"{max_content_length + 1}",
        },
    )
    assert response.status == 400
    response_json = await response.json()
    assert "image" in response_json


@pytest.mark.parametrize(
    "content_type, image_format", [("image/jpeg", "JPEG"), ("image/png", "PNG")]
)
async def test_valid_image_types(client, get_image_data, content_type, image_format):
    image_data = get_image_data(image_format=image_format)
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": content_type, "Foo": "bar"}
    )
    assert response.status == 200
    response_json = await response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 1


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
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": "image/jpeg"}
    )
    assert response.status == 400
    response_json = await response.json()
    assert "image" in response_json


@pytest.mark.parametrize(
    "width, height",
    [
        (config.colorific.image_min_width, config.colorific.image_min_height),
        (config.colorific.image_min_width, 500),
        (500, config.colorific.image_min_height),
        (config.colorific.image_max_width, config.colorific.image_max_height),
        (config.colorific.image_max_width, 500),
        (500, config.colorific.image_max_height),
    ],
)
async def test_valid_image_dimensions(client, get_image_data, width, height):
    image_data = get_image_data(size=(width, height))
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": "image/jpeg", "Foo": "bar"}
    )
    assert response.status == 200
    response_json = await response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 1


async def test_too_big_image_size(client):
    image_data = b"a" * (config.colorific.image_max_size_bytes + 1)
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": "image/jpeg"}
    )
    assert response.status == 400
    response_json = await response.json()
    assert response_json["image"] == IMAGE_TOO_LARGE_ERROR


async def test_valid_image_size(client):
    image_data = b"a" * (config.colorific.image_max_size_bytes)
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": "image/jpeg"}
    )
    assert response.status == 400
    response_json = await response.json()
    assert response_json["image"] != IMAGE_TOO_LARGE_ERROR


async def test_invalid_image_data(client, image_data):
    image_data = br"%6as7dhhjHsdsad" + image_data
    response = await client.put(
        "/image", data=image_data, headers={"Content-Type": "image/jpeg"}
    )
    assert response.status == 400
    response_json = await response.json()
    assert "image" in response_json
