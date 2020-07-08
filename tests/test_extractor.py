import numpy as np
import pytest
from PIL import Image

from colorific.extractor import Color, KMeansExtractor
from colorific.settings import config


@pytest.mark.parametrize(
    "mode, color, expected_rgb, expected_name",
    [
        ("RGB", (255, 0, 0), (255, 0, 0), "Red"),
        ("RGB", (0, 255, 0), (0, 255, 0), "Green"),
        ("RGB", (0, 0, 255), (0, 0, 255), "Blue"),
        ("L", 255, (255, 255, 255), "White"),
        ("L", 0, (0, 0, 0), "Black"),
        ("RGBA", (255, 0, 0, 128), (255, 0, 0), "Red"),
        ("RGBA", (255, 0, 0, 0), (255, 0, 0), "Red"),
        ("P", (128, 255, 0), (128, 255, 0), "Radium"),
    ],
)
def test_one_color_image(mode, color, expected_rgb, expected_name, get_one_color_image):
    extractor = KMeansExtractor()
    image = get_one_color_image(mode, color)
    colors = extractor.extract(image)
    assert len(colors) == 1
    assert colors[0].name == expected_name
    assert np.linalg.norm(np.array(colors[0].rgb) - np.array(expected_rgb)) < 10


def test_four_color_image(get_four_color_image):
    extractor = KMeansExtractor()
    image = get_four_color_image("RGB")
    colors = extractor.extract(image)
    assert len(colors) == 4


def test_small_image():
    image = Image.new(
        "RGB",
        (config.colorific.image_min_width, config.colorific.image_min_height),
        color=(0, 255, 0),
    )
    extractor = KMeansExtractor()
    colors = extractor.extract(image)
    assert len(colors) == 1


@pytest.mark.parametrize(
    "r, g, b",
    [
        (0, 0, 0),
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 0, 255),
        (255, 255, 255),
        (17, 156, 251),
        (128, 128, 128),
        (1, 1, 1),
        (78, 122, 254),
        (254, 254, 254),
    ],
)
def test_color(r, g, b):
    color = Color.from_rgb(r, g, b)
    assert color.rgb == [r, g, b]
