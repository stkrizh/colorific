import pytest
from marshmallow import ValidationError

from colorific.schema import ColorRequestSchema


@pytest.mark.parametrize(
    "color",
    [
        None,
        "",
        " ",
        "\t",
        "dfgkhfdkg",
        "0000000",
        "00000",
        "AABBCC",
        "123456 ",
        " 123456",
        "#ffffff",
    ],
)
def test_color_request_schema_invalid(color):
    schema = ColorRequestSchema()
    with pytest.raises(ValidationError) as exc:
        schema.load({"color": color})
        assert "color" in exc.value.messages


@pytest.mark.parametrize(
    "color, rgb",
    [
        ("000000", [0, 0, 0]),
        ("ffffff", [255, 255, 255]),
        ("123456", [18, 52, 86]),
        ("abcdef", [171, 205, 239]),
    ],
)
def test_color_request_schema_valid(color, rgb):
    schema = ColorRequestSchema()
    color = schema.load({"color": color})
    assert color.rgb == rgb
    assert color.red == rgb[0]
    assert color.green == rgb[1]
    assert color.blue == rgb[2]


async def test_images_created(db):
    async with db.acquire() as connection:
        cursor = await connection.execute(
            """
            SELECT COUNT(*) from image;
            """
        )
        image_count = await cursor.scalar()
        assert image_count == 5

        cursor = await connection.execute(
            """
            SELECT COUNT(*) from image_color;
            """
        )
        color_count = await cursor.scalar()
        assert color_count == 9

        cursor = await connection.execute(
            """
            SELECT SUM(percentage) AS sum from image_color GROUP BY image_id;
            """
        )
        rows = await cursor.fetchall()
        assert [row["sum"] for row in rows] == [1, 1, 1, 1, 1]


async def test_image_list(client):
    response = await client.get("/images?color=ff0000")
    assert response.status == 200
    response_json = await response.json()
    assert len(response_json) == 5
    assert {image["origin"] for image in response_json} == {"a", "b", "c", "d", "e"}


@pytest.mark.parametrize(
    "color, expected_order",
    [
        ("ff0000", [5, 1]),
        ("ffffff", [3, 4, 5, 1]),
        ("000000", [2, 1, 5]),
        ("008800", [4, 5]),
    ],
)
async def test_image_ordering(client, color, expected_order):
    response = await client.get(f"/images?color={color}")
    assert response.status == 200
    response_json = await response.json()
    assert len(response_json) == 5
    ids = [image["id"] for image in response_json]
    for expected_id, actual_id in zip(expected_order, ids):
        assert expected_id == actual_id


@pytest.mark.parametrize(
    "url",
    [
        "/images",
        "/images?color=",
        "/images?color=  ",
        "/images?color=AABBCC",
        "/images?color=#123456",
        "/images?color=1234567",
    ],
)
async def test_bad_request(client, url):
    response = await client.get(url)
    assert response.status == 400
    response_json = await response.json()
    assert "color" in response_json
