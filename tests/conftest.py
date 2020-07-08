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
from colorific.types import Color


@pytest.fixture(scope="session", autouse=True)
def sync_db_engine():
    """
    Create DB tables with synchronous DB connection.
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

    app = application.init(setup_workers=False)
    app["executor"] = executor
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture
def db(client):
    return client.server.app["db"]


@pytest.fixture
async def redis(client):
    yield client.server.app["redis"]
    await client.server.app["redis"].flushdb()


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


@pytest.fixture(scope="session", autouse=True)
def create_images(sync_db_engine):
    sync_db_engine.execute(
        """
        INSERT INTO image (id, origin, url_big, url_thumb) VALUES
        (1, 'a', 'a', 'a'),
        (2, 'b', 'b', 'b'),
        (3, 'c', 'c', 'c'),
        (4, 'd', 'd', 'd'),
        (5, 'e', 'e', 'e');
        """
    )

    colors = {
        1: [(255, 0, 0, 0.5, "'Red'", 0), (0, 0, 255, 0.5, "'Blue'", 0)],
        2: [(0, 0, 0, 1, "'Black'", 0)],
        3: [(255, 255, 255, 1, "'White'", 0)],
        4: [(0, 255, 0, 0.7, "'Green'", 0), (0, 128, 0, 0.3, "'Grey'", 0)],
        5: [
            (255, 0, 0, 0.6, "'Red'", 0),
            (0, 0, 255, 0.2, "'Blue'", 0),
            (0, 128, 0, 0.2, "'Grey'", 0),
        ],
    }
    sql: List[str] = []
    for image_id, image_colors in colors.items():
        for raw_color in image_colors:
            color = Color.from_rgb(*raw_color[:-2])
            sql.append(
                f"({image_id}, {color.L}, {color.a}, "
                f"{color.b}, {color.percentage}, {raw_color[-2]}, {raw_color[-1]})"
            )

    sync_db_engine.execute(
        f"""
        INSERT INTO image_color (image_id, "L", a, b, percentage, name, name_distance) 
        VALUES {', '.join(sql)};
        """
    )
