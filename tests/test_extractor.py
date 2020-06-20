from typing import Tuple

import numpy as np
import pytest
from PIL import Image

from colorific.extractor import KMeansExtractor


@pytest.fixture
def get_one_color_image() -> Image:
    def _one_color_image(mode: str, color: Tuple[int, int, int]):
        image = Image.new(mode, (500, 500), color=color)
        return image

    return _one_color_image


@pytest.mark.parametrize(
    "mode, color, expected_rgb",
    [
        ("RGB", (255, 0, 0), (255, 0, 0)),
        ("RGB", (0, 255, 0), (0, 255, 0)),
        ("RGB", (0, 0, 255), (0, 0, 255)),
        ("L", 255, (255, 255, 255)),
        ("L", 0, (0, 0, 0)),
        ("RGBA", (255, 0, 0, 128), (255, 0, 0)),
        ("RGBA", (255, 0, 0, 0), (255, 0, 0)),
        ("P", (128, 255, 0), (128, 255, 0)),
    ],
)
def test_one_color_image(mode, color, expected_rgb, get_one_color_image):
    extractor = KMeansExtractor()
    image = get_one_color_image(mode, color)
    colors = extractor.extract(image)
    assert len(colors) == 1
    assert np.linalg.norm(np.array(colors[0].rgb) - np.array(expected_rgb)) < 10


def test_small_image():
    image = Image.new("RGB", (1, 1), color=(0, 255, 0))
    extractor = KMeansExtractor()
    colors = extractor.extract(image)
    assert len(colors) == 1
