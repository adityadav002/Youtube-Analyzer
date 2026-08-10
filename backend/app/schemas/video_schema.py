from marshmallow import Schema, fields, validate

class VideoSchema(Schema):
    id = fields.String(dump_only=True)
    channel_id = fields.String(dump_only=True)
    title = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    duration = fields.Integer(dump_only=True)
    view_count = fields.Integer(dump_only=True)
    like_count = fields.Integer(dump_only=True)
    comment_count = fields.Integer(dump_only=True)
    upload_date = fields.DateTime(dump_only=True)
    is_short = fields.Boolean(dump_only=True)
    is_live = fields.Boolean(dump_only=True)
    live_status = fields.String(dump_only=True)
    availability = fields.String(dump_only=True)
    age_limit = fields.Integer(dump_only=True)
    has_transcript = fields.Boolean(dump_only=True)
    comments_disabled = fields.Boolean(dump_only=True)
    thumbnail_url = fields.String(dump_only=True)
    tags = fields.List(fields.String(), dump_only=True)
    categories = fields.List(fields.String(), dump_only=True)
    formats = fields.List(fields.Dict(), dump_only=True)
    chapters = fields.List(fields.Dict(), dump_only=True)
    heatmap = fields.List(fields.Dict(), dump_only=True)
    
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class VideoCreateSchema(Schema):
    url = fields.String(required=True, validate=validate.Length(min=10, max=255))
