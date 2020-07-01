"""
This module contains classes for loading and validating images from different sources.
"""
import asyncio
from abc import abstractmethod
from typing import BinaryIO, Optional, Protocol

from aiohttp import ClientError, ClientSession, ClientTimeout, StreamReader
from marshmallow import ValidationError
from PIL import Image, UnidentifiedImageError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from .settings import config


IMAGE_TOO_LARGE_ERROR = (
    f"The image file is too large. Maximum file size is "
    f"{(config.colorific.image_max_size_bytes / 2**20):.2f} Mb."
)
IMAGE_INVALID_TYPE_ERROR = (
    f"Only {', '.join(config.colorific.allowed_image_content_types)} "
    f"images are allowed."
)


class HasContentLength(Protocol):
    @property
    @abstractmethod
    def content_length(self) -> Optional[int]:
        ...


class HasContentType(Protocol):
    @property
    @abstractmethod
    def content_type(self) -> str:
        ...


@retry(
    retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
    wait=wait_fixed(config.colorific.http_client_retrying_wait_time),
    stop=stop_after_attempt(config.colorific.http_client_retrying_max_attempts),
)
async def load_by_url(client: ClientSession, url: str) -> bytes:
    """
    Read HTTP response from `url`, perform basic validation and return
    raw image bytes.

    Raises
    ------
    RetryError
        If the requested resource is not available.
    ValidationError
        If the image is not valid.
    """
    async with client.get(
        url, timeout=ClientTimeout(total=config.colorific.http_client_timeout)
    ) as response:
        response.raise_for_status()
        validate_content_type(response)
        validate_content_length(response)
        buffer = await read_bytes(response.content)

    return buffer


async def read_bytes(reader: StreamReader, chunk_size: int = 2 ** 18) -> bytes:
    """
    Read image raw bytes from `reader`.

    Raises
    ------
    ValidationError:
        If the image file is too large.
    """
    buffer = b""
    async for chunk in reader.iter_chunked(chunk_size):
        buffer += chunk
        if len(buffer) > config.colorific.image_max_size_bytes:
            raise ValidationError(IMAGE_TOO_LARGE_ERROR, field_name="image")

    return buffer


def open_image(buffer: BinaryIO) -> Image:
    """
    Convert raw bytes from `buffer` to `Image` instance
    and perform basic validation.

    Raises
    ------
    ValidationError:
        If the image is invalid.
    """
    try:
        image = Image.open(buffer)
    except UnidentifiedImageError:
        raise ValidationError("Invalid image format.", field_name="image")

    validate_image_dimensions(image)
    return image


def validate_image_dimensions(image: Image) -> None:
    """
    Validate image dimensions (width and height) and raise `ValidationError`
    if dimensions are not allowed.

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
                f"Maximum allowed image size is {max_width} x {max_height} pixels, "
                f"currently it's {image.width} x {image.height}"
            ),
            field_name="image",
        )

    min_width = config.colorific.image_min_width
    min_height = config.colorific.image_min_height

    if image.width < min_width or image.height < min_height:
        raise ValidationError(
            (
                f"Minimum allowed image size is {min_width} x {min_height} pixels, "
                f"currently it's {image.width} x {image.height}"
            ),
            field_name="image",
        )


def validate_content_type(obj: HasContentType) -> None:
    """
    Raise `ValidationError` if content type is not allowed.
    """
    allowed_content_types = config.colorific.allowed_image_content_types

    if obj.content_type not in allowed_content_types:
        raise ValidationError(IMAGE_INVALID_TYPE_ERROR, field_name="image")


def validate_content_length(obj: HasContentLength) -> None:
    """
    Raise `ValidationError` if content length is over the maximum limit
    defined in `config.yaml`
    """
    max_content_length: int = config.colorific.image_max_size_bytes
    content_length: Optional[int] = obj.content_length

    if not content_length:
        raise ValidationError(
            "Content-Length HTTP-header must be set.", field_name="content_length"
        )

    if content_length > max_content_length:
        raise ValidationError(IMAGE_TOO_LARGE_ERROR, field_name="image")
