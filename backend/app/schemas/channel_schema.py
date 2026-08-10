from marshmallow import Schema, fields, validate, EXCLUDE

class ChannelSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.String(dump_only=True)
    handle = fields.String(allow_none=True)
    display_name = fields.String()
    description = fields.String(allow_none=True)
    avatar_url = fields.String(allow_none=True)
    banner_url = fields.String(allow_none=True)
    subscriber_count = fields.Integer()
    video_count = fields.Integer()
    view_count = fields.Integer(allow_none=True)
    is_verified = fields.Boolean()
    country = fields.String(allow_none=True)
    rss_monitoring = fields.Boolean()
    last_crawled_at = fields.DateTime(allow_none=True)
    join_date = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class ChannelCreateSchema(Schema):
    url = fields.String(required=True, validate=validate.Length(min=1))

class ChannelUpdateSchema(Schema):
    rss_monitoring = fields.Boolean()
