import pytest


@pytest.mark.parametrize(
    "image_id", ["", "   100 ", "\t", "dfgkhfdkg", "'"],
)
async def test_image_id_invalid(client, image_id):
    response = await client.get(f"/images/{image_id}")
    assert response.status == 404


async def test_image_detail_not_found(client):
    response = await client.get("/images/6")
    assert response.status == 404
    response_json = await response.json()
    assert "image" in response_json


@pytest.mark.parametrize(
    "image_id, placeholder", [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e")],
)
async def test_image_detail_valid_request(client, image_id, placeholder):
    response = await client.get(f"/images/{image_id}")
    assert response.status == 200
    response_json = await response.json()
    assert "image" in response_json
    assert "colors" in response_json

    assert sum(color["percentage"] for color in response_json["colors"]) == 1
    assert all(isinstance(color["name"], str) for color in response_json["colors"])
    assert all(
        isinstance(color["name_distance"], float) for color in response_json["colors"]
    )

    assert response_json["image"]["origin"] == placeholder
    assert response_json["image"]["url_big"] == placeholder
    assert response_json["image"]["url_thumb"] == placeholder
