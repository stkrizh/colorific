from marshmallow import Schema, fields


class ColorSchema(Schema):
    r = fields.Integer()
    g = fields.Integer()
    b = fields.Integer()
    percentage = fields.Float()


class UploadURLRequestSchema(Schema):
    url = fields.URL(schemes={"http", "https"})
