from marshmallow import Schema, fields

class ProcessingLogSchema(Schema):
    id = fields.Int(dump_only=True)
    project_id = fields.Str(required=True)
    document_id = fields.Str(required=True)
    status = fields.Str(required=True)
    processed_at = fields.DateTime(dump_only=True)