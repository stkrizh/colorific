import asyncio
import json
import logging
import sys
from typing import List, Optional

from aiohttp.web import HTTPBadRequest, Response, View, json_response
from marshmallow import ValidationError
from tenacity import RetryError

from . import image_loader
from .extractor import Color, KMeansExtractor
from .schema import ColorSchema, UploadURLRequestSchema


LOG = logging.getLogger(__file__)


class ColorExtractionView(View):
    """
    Main API-endpoint for color extraction.
    """

    async def options(self) -> Response:
        return Response(status=200, headers={"Content-Type": "text/plain"})

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
            image_data = await image_loader.load_by_url(
                self.request.app["http_client"], request["url"]
            )
        except RetryError as error:
            LOG.debug(error, exc_info=sys.exc_info())
            raise self.bad_request(url=["The requested resource is not available."])
        except ValidationError as error:
            LOG.debug(error)
            raise self.bad_request(**error.normalized_messages())

        response = await self.extract_colors(image_data)
        return response

    async def handle_binary_request(self) -> Response:
        """
        Handler for direct image uploading in request body.
        """
        try:
            image_loader.validate_content_type(self.request)
            image_loader.validate_content_length(self.request)
            image_data = await image_loader.read_bytes(self.request.content)
        except ValidationError as error:
            LOG.debug(error)
            raise self.bad_request(**error.normalized_messages())

        response = await self.extract_colors(image_data)
        return response

    async def extract_colors(self, image_data: bytes) -> Response:
        """
        Run color extraction algorithm in process pool executor, and
        return HTTP response with extracted colors.
        """
        loop = asyncio.get_running_loop()
        try:
            color_extractor = KMeansExtractor()
            colors: List[Color] = await loop.run_in_executor(
                self.request.app["executor"],
                color_extractor.extract_from_bytes,
                image_data,
            )
        except ValidationError as error:
            raise self.bad_request(**error.normalized_messages())

        schema = ColorSchema()
        return json_response(schema.dump(colors, many=True))

    def bad_request(self, body: Optional[dict] = None, **kwargs) -> HTTPBadRequest:
        """
        Return HTTP 400 response with JSON-encoded body.
        """
        return HTTPBadRequest(
            text=json.dumps(body if body is not None else kwargs),
            content_type="application/json",
        )
