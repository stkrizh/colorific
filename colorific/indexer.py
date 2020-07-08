import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from itertools import count, cycle
from typing import AsyncIterable, Iterable, List, Optional, Tuple

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
from .extractor import ColorExtractor
from .settings import config
from .types import Color, Image


LOG = logging.getLogger(__name__)


class ImageIndexer(ABC):
    """
    Base class for image indexing.
    """

    color_extractor: ColorExtractor
    executor: Executor
    http_client: ClientSession
    periodicity: int
    rewrite_existing_images: bool

    @abstractmethod
    async def get_images(self) -> AsyncIterable[List[Image]]:
        """
        Get images for indexing.
        """
        yield []

    @abstractmethod
    async def commit(self, image: Image, colors: List[Color]) -> None:
        """
        Save image and extracted main colors.
        """
        ...

    @abstractmethod
    async def is_image_already_indexed(self, image: Image) -> bool:
        """
        Check whether the image is already indexed.
        """
        ...

    async def run(self):
        """
        Entry point for image indexing.
        """
        async for images in self.get_images():
            await self.index_many(images)
        LOG.info("Image indexing has been completed.")

    async def index(self, image: Image) -> Tuple[Image, bool]:
        """
        Extract main colors for `image` and save the data.
        """
        if not self.rewrite_existing_images and (
            await self.is_image_already_indexed(image)
        ):
            LOG.debug(f"Image {image.origin} is already indexed.")
            return image, False

        try:
            image_data: bytes = await image_loader.load_by_url(
                self.http_client, image.url_big
            )
            LOG.debug(f"Image data loaded for {image.origin}.")
            colors: List[Color] = await self.extract_colors(image_data)
            LOG.debug(f"Colors for {image.origin} have been extracted.")
        except RetryError:
            LOG.error(
                f"Could not load image from {image.url_big}", exc_info=sys.exc_info()
            )
            return image, False
        except ValidationError as error:
            LOG.warning(
                f"Validation error is raised for {image.url_big}: "
                f"{error.normalized_messages()}"
            )
            return image, False

        await self.commit(image, colors)
        return image, True

    async def index_many(self, images: List[Image]) -> None:
        """
        Run indexing concurrently for the list of images.
        """
        total_indexed: int = 0
        total_skipped: int = 0

        for ix, coro in enumerate(
            asyncio.as_completed([self.index(image) for image in images]), start=1,
        ):
            image, indexed = await coro
            if indexed:
                LOG.debug(f"Indexed ({ix} of {len(images)}): {image.origin}")
                total_indexed += 1
            else:
                LOG.debug(f"Skipped ({ix} of {len(images)}): {image.origin}")
                total_skipped += 1

        LOG.info(f"Total indexed images: {total_indexed}; skipped: {total_skipped}.")

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
        executor: Executor,
        http_client: ClientSession,
        db_pool: Engine,
        cyclic: bool = config.colorific.image_indexing_cyclic,
        rewrite_existing_images: bool = config.colorific.image_indexing_rewrite_existing,
        start_page: int = config.unsplash.start_page,
        end_page: int = config.unsplash.end_page,
        periodicity: int = config.colorific.image_indexing_interval_sec,
    ):
        assert start_page > 0
        assert periodicity > 0

        self.color_extractor = color_extractor
        self.executor = executor
        self.http_client = http_client
        self.db_pool = db_pool
        self.rewrite_existing_images = rewrite_existing_images
        self.periodicity = periodicity
        self.page_num_iterator: Iterable[int] = (
            count(start_page) if end_page < 0 else range(start_page, end_page + 1)
        )
        if cyclic:
            self.page_num_iterator = cycle(self.page_num_iterator)

    async def get_images(self) -> AsyncIterable[List[Image]]:
        """
        Yield image list periodically.
        """
        for page_num in self.page_num_iterator:
            try:
                images = await self.get_images_for_page(page_num)
            except RetryError:
                LOG.exception(f"Could not load images for page {page_num}.")
                await asyncio.sleep(self.periodicity)
                continue

            if not images:
                break

            yield images
            await asyncio.sleep(self.periodicity)

    @retry(
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(config.colorific.http_client_retrying_max_attempts),
        wait=wait_fixed(config.colorific.http_client_retrying_wait_time),
    )
    async def get_images_for_page(self, page_num: int) -> List[Image]:
        """
        Get a list of latest images for page `page_num`
        """
        LOG.debug(f"Getting images for page {page_num}.")
        async with self.http_client.get(
            self.base_url,
            params={"page": page_num, "per_page": 30, "order_by": "popular"},
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
            LOG.info(f"Got {len(images)} images for page {page_num}.")
            return images

    async def is_image_already_indexed(self, image: Image) -> bool:
        """
        Check whether the image is already indexed.
        """
        async with self.db_pool.acquire() as connection:
            query = (
                sa.select([db.image.c.id])
                .select_from(db.image)
                .where(db.image.c.origin == image.origin)
            )
            cursor = await connection.execute(query)
            image_id: Optional[int] = await cursor.scalar()
            return isinstance(image_id, int)

    async def commit(self, image: Image, colors: List[Color]) -> None:
        """
        Save image data and extracted colors to DB.
        """
        async with self.db_pool.acquire() as connection:
            async with connection.begin():
                await connection.execute(
                    db.image_color.delete()
                    .where(db.image_color.c.image_id == db.image.c.id)
                    .where(db.image.c.origin == image.origin)
                )
                await connection.execute(
                    db.image.delete().where(db.image.c.origin == image.origin)
                )
                LOG.debug(f"Image {image.origin} has been deleted from DB.")
                image_id: int = await self.create_image(connection, image)
                LOG.debug(f"Image {image.origin} has been inserted to DB.")
                for color in colors:
                    await connection.execute(
                        db.image_color.insert().values(
                            image_id=image_id,
                            L=color.L,
                            a=color.a,
                            b=color.b,
                            percentage=color.percentage,
                            name=color.name,
                            name_distance=color.name_distance,
                        )
                    )
                LOG.debug(f"Colors for {image.origin} have been added to DB.")

    async def create_image(self, connection, image: Image) -> int:
        """
        Create new image and return the ID.
        """
        query = (
            db.image.insert()
            .values(
                origin=image.origin, url_big=image.url_big, url_thumb=image.url_thumb,
            )
            .returning(db.image.c.id)
        )
        cursor = await connection.execute(query)
        new_image_id: int = await cursor.scalar()
        return new_image_id
