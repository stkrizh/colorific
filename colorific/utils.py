from io import BytesIO
from typing import List

from marshmallow import ValidationError
from PIL import Image, UnidentifiedImageError

from .extractor import Color, KMeansExtractor
from .settings import config


def extract_colors(image_data: bytes) -> List[Color]:
    """
    Helper method for color extraction.
    """
    extractor = KMeansExtractor()
    image = convert_bytes_to_image(image_data)
    colors = extractor.extract(image)
    return colors


def convert_bytes_to_image(image_data: bytes) -> Image:
    """
    Convert raw bytes to `Image` instance and perform basic validation.

    Raises
    ------
    ValidationError:
        If image is invalid.
    """
    try:
        with BytesIO(image_data) as buffer:
            image = Image.open(buffer)
    except UnidentifiedImageError:
        raise ValidationError("Invalid image format.", field_name="image")

    validate_image_dimensions(image)
    return image


def validate_image_dimensions(image: Image) -> None:
    """
    Valdiate image dimensions (width and height) and raise `ValidationError`
    if dimensionas are not allowed.

    Raises
    ------
    ValidationError:
        If image dimensions are not allowed.
    """
    max_width = config.colorific.image_max_width
    max_height = config.colorific.image_max_height

    if image.width > max_width or image.height > max_height:
        raise ValidationError(
            (
                "Maximum allowed image size is {max_width} x {max_height} pixels, "
                "currently it's {image.width} x {image.height}"
            ),
            field_name="image",
        )

    min_width = config.colorific.image_min_width
    min_height = config.colorific.image_min_height

    if image.width < min_width or image.height < min_height:
        raise ValidationError(
            (
                "Minimum allowed image size is {min_width} x {min_height} pixels, "
                "currently it's {image.width} x {image.height}"
            ),
            field_name="image",
        )
