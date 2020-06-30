import asyncio
import logging
import sys
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from dataclasses import dataclass
from typing import List

from aiohttp import ClientSession
from marshmallow import ValidationError
from tenacity import RetryError

from . import image_loader
from .extractor import Color, ColorExtractor
from .utils import extract_colors

LOG = logging.getLogger(__name__)


@dataclass
class Image:
    origin: str
    big_url: str
    small_url: str


class ImageIndexer(ABC):
    """
    Base class for images indexing.
    """

    http_client: ClientSession
    color_extractor: ColorExtractor
    pool: Executor

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

    async def index_many(self, images: List[Image]) -> None:
        await asyncio.wait([self.index(image) for image in images])

    async def index(self, image: Image) -> None:
        """
        Extract main colors for `image` and save the data.
        """
        try:
            image_data: bytes = await image_loader.load_by_url(
                self.http_client, image.big_url
            )
            colors: List[Color] = await self.extract_colors(image_data)
        except RetryError:
            LOG.info(
                f"Could not load image from {image.big_url}", exc_info=sys.exc_info()
            )
            return
        except ValidationError as error:
            LOG.info(
                f"Validation error is raised for {image.big_url}: "
                f"{error.normalized_messages()}"
            )
            return

        await self.commit(image, colors)

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
            self.pool, extract_colors, image_data, self.color_extractor
        )
        return colors
