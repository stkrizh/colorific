# flake8:noqa
# isort:skip_file
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO
from typing import List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw

from colorific import settings

settings.setup("test")

from colorific import application
from colorific import db as colorific_db


@pytest.fixture(scope="session", autouse=True)
def sync_db():
    """
    Synchronous DB connection.
    """
    engine = colorific_db.create_engine()
    colorific_db.METADATA.drop_all(engine)
    colorific_db.METADATA.create_all(engine)
    yield engine
    colorific_db.METADATA.drop_all(engine)


@pytest.fixture(scope="session")
def executor():
    """
    Process pool executor.
    Without this fixture, pool would start up on every test.
    """
    executor = ProcessPoolExecutor(max_workers=1)
    yield executor
    executor.shutdown()


@pytest.fixture
def client(loop, aiohttp_client, executor):
    """
    Aiohttp test client.
    """

    app = application.init(setup_workers=False, setup_indexing=False)
    app["executor"] = executor
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture
def db(client):
    return client.server.app["db"]


@pytest.fixture
async def clean_tables(client):
    """
    Clean DB tables after a test completes.
    """
    yield
    async with client.server.app["db"].acquire() as connection:
        await connection.execute(colorific_db.image_color.delete())
        await connection.execute(colorific_db.image.delete())


@pytest.fixture(scope="session")
def get_one_color_image() -> Image:
    def _get_image(
        mode: str, color: Tuple[int, int, int], size: Tuple[int, int] = (500, 500)
    ):
        image = Image.new(mode, size, color=color)
        return image

    return _get_image


@pytest.fixture
def get_four_color_image(scope="session") -> Image:
    def _get_image(mode: str, colors: Optional[List[Tuple[int, int, int]]] = None):
        colors = (
            [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 0, 255)]
            if colors is None
            else colors
        )
        assert len(colors) == 4
        image = Image.new(mode, (500, 500))
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, 250, 250], fill=colors[0])
        draw.rectangle([250, 0, 500, 250], fill=colors[1])
        draw.rectangle([0, 250, 250, 500], fill=colors[2])
        draw.rectangle([250, 250, 500, 500], fill=colors[3])
        return image

    return _get_image


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
