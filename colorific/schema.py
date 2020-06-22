from marshmallow import Schema, fields


class ColorSchema(Schema):
    r = fields.Integer()
    g = fields.Integer()
    b = fields.Integer()
    percentage = fields.Float()
