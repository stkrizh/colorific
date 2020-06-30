from io import BytesIO
from typing import List

from .extractor import Color, ColorExtractor
from .image_loader import open_image


def extract_colors(image_data: bytes, color_extractor: ColorExtractor) -> List[Color]:
    """
    Helper method for color extraction.
    """
    with BytesIO(image_data) as buffer:
        image = open_image(buffer)
        colors = color_extractor.extract(image)
        return colors
