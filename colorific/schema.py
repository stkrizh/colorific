import re

from marshmallow import Schema, ValidationError, fields, post_load, validates

from .types import Color


COLOR_PATTERN = re.compile(r"^#[0-9a-f]{6}$")


class ColorRequestSchema(Schema):
    color = fields.String(
        allow_none=False,
        required=True,
        error_messages={"required": "Color must be defined."},
    )

    @validates("color")
    def validate_color(self, value):
        if not COLOR_PATTERN.match(value):
            raise ValidationError("Invalid color format.")

    @post_load
    def make(self, data, *args, **kwargs) -> Color:
        rgb: str = data["color"]
        return Color.from_rgb(
            r=int(rgb[1:3], 16), g=int(rgb[3:5], 16), b=int(rgb[5:7], 16)
        )


class ColorSchema(Schema):
    r = fields.Integer()
    g = fields.Integer()
    b = fields.Integer()
    percentage = fields.Float()


class ImageResponseSchema(Schema):
    origin = fields.URL()
    url_big = fields.URL()
    url_thumb = fields.URL()
    id = fields.Integer()


class UploadURLRequestSchema(Schema):
    url = fields.URL(schemes={"http", "https"})
