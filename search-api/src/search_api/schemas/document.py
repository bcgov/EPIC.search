"""Document schema definitions."""
from marshmallow import EXCLUDE, Schema, fields

class DocumentDownloadSchema(Schema):
    """Document Download Schema"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""
        unknown = EXCLUDE

    s3_key = fields.Str(data_key="s3_key", required=True)
