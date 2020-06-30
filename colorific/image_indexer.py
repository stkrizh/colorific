import asyncio
from abc import ABC, abstractmethod
from concurrent.futures import Executor
from dataclasses import dataclass
from typing import List

from .extractor import Color, ColorExtractor
from .utils import extract_colors


@dataclass
class Image:
    origin: str
    big_url: str
    small_url: str


class ImageIndexer(ABC):
    """
    Base class for images indexing.
    """

    color_extractor: ColorExtractor
    pool: Executor

    @abstractmethod
    async def index(self, image: Image) -> None:
        ...

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
