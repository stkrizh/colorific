import asyncio
import json
from typing import List, Optional

from aiohttp import StreamReader
from aiohttp.web import HTTPBadRequest, Response, View, json_response
from marshmallow import ValidationError

from .extractor import Color
from .schema import ColorSchema
from .settings import config
from .utils import extract_colors

IMAGE_TOO_LARGE_ERROR = (
    f"The image file is too large. Maximum file size is "
    f"{config.colorific.image_max_size_bytes} Mb."
)
IMAGE_INVALID_TYPE_ERROR = (
    f"Only {', '.join(config.colorific.allowed_image_content_types)} "
    f"images are allowed."
)


class ColorExtractionView(View):
    """
    Main API-endpoint for color extraction.
    """

    async def put(self) -> Response:
        if self.request.content_type == "application/json":
            return await self.handle_json_request()
        return await self.handle_binary_request()

    async def handle_json_request(self) -> Response:
        # TODO: implement passing image by URL
        request = await self.request.json()
        return json_response({"status": "OK", "request": request})

    async def handle_binary_request(self) -> Response:
        """
        Handler for direct image uploading in request body.
        """
        self.validate_content_type()
        self.validate_content_length()

        buffer = await self.read_bytes(self.request.content)
        loop = asyncio.get_running_loop()
        try:
            colors: List[Color] = await loop.run_in_executor(
                self.request.app["executor"], extract_colors, buffer,
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
        async for chunk in self.request.content.iter_chunked(chunk_size):
            buffer += chunk
            if len(buffer) > config.colorific.image_max_size_bytes:
                raise self.bad_request(image=IMAGE_TOO_LARGE_ERROR)

        return buffer

    def validate_content_type(self) -> None:
        """
        Raise `HTTPBadRequest` if request content type is not allowed.
        """
        allowed_content_types = config.colorific.allowed_image_content_types

        if self.request.content_type not in allowed_content_types:
            raise self.bad_request(image=IMAGE_INVALID_TYPE_ERROR)

    def validate_content_length(self) -> int:
        """
        Raise `HTTPBadRequest` if request content length is over the maximum limit
        defined in `config.yaml`
        """
        max_content_length: int = config.colorific.image_max_size_bytes
        content_length: Optional[int] = self.request.content_length

        if content_length is None:
            raise self.bad_request(
                content_length="Content-Length HTTP-header must be set."
            )

        if content_length > max_content_length:
            raise self.bad_request(image=IMAGE_TOO_LARGE_ERROR)

        return content_length

    def bad_request(self, body: Optional[dict] = None, **kwargs) -> HTTPBadRequest:
        """
        Return HTTP 400 response with JSON-encoded body.
        """
        return HTTPBadRequest(
            text=json.dumps(body if body is not None else kwargs),
            content_type="application/json",
        )
