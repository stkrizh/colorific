import asyncio
import json
import logging
import sys
from typing import List, Optional, Protocol

from aiohttp import ClientError, ClientTimeout, StreamReader
from aiohttp.web import HTTPBadRequest, Response, View, json_response
from marshmallow import ValidationError
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from .extractor import Color
from .schema import ColorSchema, UploadURLRequestSchema
from .settings import config
from .utils import extract_colors

LOG = logging.getLogger(__file__)


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
    def content_length(self) -> Optional[int]:
        ...


class HasContentType(Protocol):
    @property
    def content_type(self) -> str:
        ...


class ColorExtractionView(View):
    """
    Main API-endpoint for color extraction.
    """

    async def put(self) -> Response:
        if self.request.content_type == "application/json":
            return await self.handle_json_request()
        return await self.handle_binary_request()

    async def handle_json_request(self) -> Response:
        schema = UploadURLRequestSchema()
        try:
            request = schema.load(await self.request.json())
        except ValidationError as error:
            raise self.bad_request(**error.normalized_messages())

        try:
            image_data = await self.download_image_by_url(request["url"])
        except RetryError as error:
            LOG.debug(error, exc_info=sys.exc_info())
            raise self.bad_request(url="The requested resource is not available.")

        response = await self.extract_colors(image_data)
        return response

    async def handle_binary_request(self) -> Response:
        """
        Handler for direct image uploading in request body.
        """
        self.validate_content_type(self.request)
        self.validate_content_length(self.request)

        image_data = await self.read_bytes(self.request.content)
        response = await self.extract_colors(image_data)
        return response

    async def extract_colors(self, image_data: bytes) -> Response:
        """
        Run color extraction algorithm in process pool executor, and
        return HTTP response with extracted colors.
        """
        loop = asyncio.get_running_loop()
        try:
            colors: List[Color] = await loop.run_in_executor(
                self.request.app["executor"], extract_colors, image_data,
            )
        except ValidationError as error:
            raise self.bad_request(**error.normalized_messages())

        schema = ColorSchema()
        return json_response(schema.dump(colors, many=True))

    async def read_bytes(
        self, reader: StreamReader, chunk_size: int = 2 ** 18
    ) -> bytes:
        """
        Read raw bytes from request body.
        """
        buffer = b""
        async for chunk in reader.iter_chunked(chunk_size):
            buffer += chunk
            if len(buffer) > config.colorific.image_max_size_bytes:
                raise self.bad_request(image=IMAGE_TOO_LARGE_ERROR)

        return buffer

    @retry(
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        wait=wait_fixed(config.colorific.http_client_retrying_wait_time),
        stop=stop_after_attempt(config.colorific.http_client_retrying_max_attempts),
    )
    async def download_image_by_url(self, url: str) -> bytes:
        """
        Read HTTP response from `url`, perform basic validation and return
        raw image bytes.

        Raises
        ------
        RetryError
            If the requested resource is not available.
        """
        async with self.request.app["http_client"].get(
            url, timeout=ClientTimeout(total=config.colorific.http_client_timeout)
        ) as response:
            response.raise_for_status()

            self.validate_content_type(response)
            self.validate_content_length(response)

            buffer = await self.read_bytes(response.content)

        return buffer

    def validate_content_type(self, obj: HasContentType) -> None:
        """
        Raise `HTTPBadRequest` if request content type is not allowed.
        """
        allowed_content_types = config.colorific.allowed_image_content_types

        if obj.content_type not in allowed_content_types:
            raise self.bad_request(image=IMAGE_INVALID_TYPE_ERROR)

    def validate_content_length(self, obj: HasContentLength) -> None:
        """
        Raise `HTTPBadRequest` if request content length is over the maximum limit
        defined in `config.yaml`
        """
        max_content_length: int = config.colorific.image_max_size_bytes
        content_length: Optional[int] = obj.content_length

        if not content_length:
            raise self.bad_request(
                content_length="Content-Length HTTP-header must be set."
            )

        if content_length > max_content_length:
            raise self.bad_request(image=IMAGE_TOO_LARGE_ERROR)

    def bad_request(self, body: Optional[dict] = None, **kwargs) -> HTTPBadRequest:
        """
        Return HTTP 400 response with JSON-encoded body.
        """
        return HTTPBadRequest(
            text=json.dumps(body if body is not None else kwargs),
            content_type="application/json",
        )
