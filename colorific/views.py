import asyncio
import json
import logging
import sys
from typing import TYPE_CHECKING, List, Optional

from aiohttp.web import (
    HTTPBadRequest,
    HTTPTooManyRequests,
    Response,
    View,
    json_response,
)
from marshmallow import ValidationError
from tenacity import RetryError

from . import image_loader
from .extractor import Color, KMeansExtractor
from .rate_limit import RateLimit, RateLimitExceeded
from .schema import (
    ColorRequestSchema,
    ColorSchema,
    ImageDetailResponseSchema,
    ImageResponseSchema,
    UploadURLRequestSchema,
)
from .services import get_image, get_image_colors, get_images_by_color
from .settings import config
from .types import Image


LOG = logging.getLogger(__file__)
SERVICE_UNAVAILABLE_ERROR = (
    "We're sorry, the service is temporarily unavailable due to many requests. "
    "Please try again a bit later."
)

if TYPE_CHECKING:
    _base = View
else:
    _base = object


class ViewMixin(_base):
    """
    Mixin with a set of helper methods.
    """

    rate_limit: Optional[RateLimit] = None

    def bad_request(self, body: Optional[dict] = None, **kwargs) -> HTTPBadRequest:
        """
        Return HTTP 400 response with JSON-encoded body.
        """
        return HTTPBadRequest(
            text=json.dumps(body if body is not None else kwargs),
            content_type="application/json",
        )

    async def ensure_rate_limit(self) -> None:
        """
        Raise HTTP exception with 429 status code if the rate limit is exceeded.
        """
        if self.rate_limit is not None:
            try:
                await self.rate_limit.ensure(self.request)
            except RateLimitExceeded as error:
                error_msg, ttl = error.args
                raise HTTPTooManyRequests(
                    text=json.dumps({"error": error_msg}),
                    content_type="application/json",
                    headers={"Retry-After": str(ttl)},
                )


class ColorExtractionView(ViewMixin, View):
    """
    Main API-endpoint for color extraction.
    """

    rate_limit = RateLimit(
        name="color_extraction",
        time_interval=config.rate_limit.color_extraction_ip_time_interval,
        limit=config.rate_limit.color_extraction_ip_limit,
        error=(
            "You've been trying to upload too many images, "
            "please try again a bit later."
        ),
    )

    async def options(self) -> Response:
        return Response(status=200, headers={"Content-Type": "text/plain"})

    async def put(self) -> Response:
        await self.ensure_rate_limit()

        semaphore = self.request.app["color_extraction_semaphore"]
        if semaphore.locked():
            return json_response({"error": SERVICE_UNAVAILABLE_ERROR}, status=503)

        async with semaphore:
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


class ImageListView(ViewMixin, View):
    """
    Search images by color.
    """

    rate_limit = RateLimit(
        name="image_search",
        time_interval=config.rate_limit.image_search_ip_time_interval,
        limit=config.rate_limit.image_search_ip_limit,
        error=(
            "You've made too many requests to the service, "
            "please try again a bit later."
        ),
    )

    async def get(self) -> Response:
        await self.ensure_rate_limit()

        input_schema = ColorRequestSchema()
        try:
            color: Color = input_schema.load(self.request.query)
        except ValidationError as error:
            raise self.bad_request(**error.normalized_messages())

        async with self.request.app["db"].acquire() as connection:
            images = await get_images_by_color(connection, color)

        output_schema = ImageResponseSchema()
        return json_response(output_schema.dump(images, many=True))


class ImageDetailView(ViewMixin, View):
    """
    Detail information about specific image.
    """

    async def get(self) -> Response:
        async with self.request.app["db"].acquire() as connection:
            image_id: int = self.request.match_info["image_id"]
            image: Optional[Image] = await get_image(connection, image_id)

            if image is None:
                return json_response({"image": "Not Found."}, status=404)

            colors: List[Color] = await get_image_colors(connection, image_id)

        output_schema = ImageDetailResponseSchema()
        return json_response(output_schema.dump({"image": image, "colors": colors}))
