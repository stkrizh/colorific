import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from dataclasses import dataclass
from typing import List, Optional, Tuple

import sqlalchemy as sa
from aiohttp import ClientError, ClientSession, ClientTimeout
from aiopg.sa import Engine
from marshmallow import ValidationError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from . import db, image_loader
from .extractor import Color, ColorExtractor
from .settings import config


LOG = logging.getLogger(__name__)


@dataclass
class Image:
    origin: str
    url_big: str
    url_thumb: str


class ImageIndexer(ABC):
    """
    Base class for image indexing.
    """

    http_client: ClientSession
    color_extractor: ColorExtractor
    executor: Executor
    periodicity: int

    @abstractmethod
    async def get_images(self) -> List[Image]:
        """
        Get images for indexing.
        """
        ...

    @abstractmethod
    async def commit(self, image: Image, colors: List[Color]) -> None:
        """
        Save image and extracted main colors.
        """
        ...

    async def run(self):
        """
        Entry point for image indexing.
        """
        while True:
            try:
                images = await self.get_images()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                LOG.warning(error)
            else:
                if not images:
                    return
                await self.index_many(images)
            await asyncio.sleep(self.periodicity)

    async def index(self, image: Image) -> Image:
        """
        Extract main colors for `image` and save the data.
        """
        try:
            image_data: bytes = await image_loader.load_by_url(
                self.http_client, image.url_big
            )
            colors: List[Color] = await self.extract_colors(image_data)
        except RetryError:
            LOG.warning(
                f"Could not load image from {image.url_big}", exc_info=sys.exc_info()
            )
            return image
        except ValidationError as error:
            LOG.warning(
                f"Validation error is raised for {image.url_big}: "
                f"{error.normalized_messages()}"
            )
            return image

        await self.commit(image, colors)
        return image

    async def index_many(self, images: List[Image]) -> None:
        """
        Run indexing concurrently for the list of images.
        """
        for ix, coro in enumerate(
            asyncio.as_completed([self.index(image) for image in images]), start=1
        ):
            image: Image = await coro
            LOG.debug(f"Indexed ({ix} of {len(images)}): {image.url_big}")

    async def extract_colors(self, image_data: bytes) -> List[Color]:
        """
        Extract palette of main colors from `image_data` in
        pool executor.

        Raises
        ------
        ValidationError:
            If the image is invalid.
        """
        loop = asyncio.get_running_loop()
        colors = await loop.run_in_executor(
            self.executor, self.color_extractor.extract_from_bytes, image_data
        )
        return colors


class UnsplashIndexer(ImageIndexer):
    """
    Image indexer for images from unsplash.com.
    """

    base_url = "https://api.unsplash.com/photos"

    def __init__(
        self,
        color_extractor: ColorExtractor,
        http_client: ClientSession,
        executor: Executor,
        db_pool: Engine,
        rewrite: bool = True,
        start_page: int = config.unsplash.start_page,
        end_page: int = config.unsplash.end_page,
        periodicity: int = config.unsplash.indexing_interval_sec,
    ):
        self.color_extractor = color_extractor
        self.http_client = http_client
        self.executor = executor
        self.db_pool = db_pool
        self.rewrite = rewrite
        self.start_page = start_page
        self.end_page = end_page
        self.current_page = self.start_page
        self.periodicity = periodicity

    @retry(
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(config.colorific.http_client_retrying_max_attempts),
        wait=wait_fixed(config.colorific.http_client_retrying_wait_time),
    )
    async def get_images(self) -> List[Image]:
        """
        Get a list of images from `self.current_page`.
        """
        LOG.debug(f"Getting images for page {self.current_page}.")
        async with self.http_client.get(
            self.base_url,
            params={"page": self.current_page, "per_page": 30},
            headers={"Authorization": f"Client-ID {config.unsplash.access_key}"},
            timeout=ClientTimeout(total=config.colorific.http_client_timeout),
        ) as response:
            response.raise_for_status()
            data = await response.json()
            images = [
                Image(
                    origin=item["links"]["html"],
                    url_big=item["urls"]["regular"],
                    url_thumb=item["urls"]["small"],
                )
                for item in data
            ]
            self.current_page += 1
            LOG.debug(f"Got {len(images)} for page {self.current_page}.")
            return images

    async def commit(self, image: Image, colors: List[Color]) -> None:
        """
        Save image data and extracted colors to DB.
        """
        async with self.db_pool.acquire() as connection:
            async with connection.begin():
                image_id, is_new = await self.get_or_create_image(connection, image)
                if not (is_new or self.rewrite):
                    return
                await connection.execute(
                    db.image_color.delete().where(db.image_color.c.image_id == image_id)
                )
                for color in colors:
                    await connection.execute(
                        db.image_color.insert().values(
                            image_id=image_id,
                            L=color.L,
                            a=color.a,
                            b=color.b,
                            percentage=color.percentage,
                        )
                    )
                await connection.execute(
                    db.image.update()
                    .values(indexed_at=sa.text("now() at time zone 'utc'"))
                    .where(db.image.c.id == image_id)
                )

    async def get_or_create_image(self, connection, image: Image) -> Tuple[int, bool]:
        """
        Return image ID from DB (create the new one if it's needed)
        """
        query = (
            sa.select([db.image.c.id])
            .select_from(db.image)
            .where(db.image.c.origin == image.origin)
        )
        cursor = await connection.execute(query)
        image_id: Optional[int] = await cursor.scalar()

        if isinstance(image_id, int):
            return image_id, False

        query = (
            db.image.insert()
            .values(
                origin=image.origin, url_big=image.url_big, url_thumb=image.url_thumb,
            )
            .returning(db.image.c.id)
        )
        cursor = await connection.execute(query)
        new_image_id: int = await cursor.scalar()
        return new_image_id, True
