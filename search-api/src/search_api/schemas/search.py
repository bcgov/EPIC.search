"""Engagement model class.

Manages the engagement
"""

from marshmallow import EXCLUDE, Schema, fields

class DocumentSchema(Schema):
    """Documents schema."""

    # document_record_id = fields.Str(data_key="document_record_id")
    # document_id = fields.Str(data_key="document_id")
    # document_label = fields.Str(data_key="document_label")
    # document_link = fields.Str(data_key="document_link")
    # document_file_name = fields.Str(data_key="document_file_name")
    # document_category_id = fields.Str(data_key="document_category_id")
    # document_category = fields.Str(data_key="document_category")
    # document_types = fields.List(fields.Str(), data_key="document_types")
    # document_type_id = fields.Int(data_key="document_type_id")
    # date_issued = fields.Str(data_key="date_issued")
    # year_issued = fields.Int(data_key="year_issued")
    # act = fields.Int(data_key="act")
    # project_id = fields.Str(data_key="project_id")
    # first_nations = fields.List(fields.Str(), data_key="first_nations")
    # consultation_records_required = fields.Bool(data_key="consultation_records_required")
    # status = fields.Bool(data_key="status")
    # amendment_count = fields.Int(data_key="amendment_count")
    # is_latest_amendment_added = fields.Bool(data_key="is_latest_amendment_added")
    # project_name = fields.Str(data_key="project_name")
    document_id = fields.Str(data_key="document_id")
    document_type = fields.Str(data_key="document_type")
    document_name = fields.Str(data_key="document_name")
    document_saved_name = fields.Str(data_key="document_saved_name")
    page_number = fields.Str(data_key="page_number")
    project_id = fields.Str(data_key="project_id")
    project_name = fields.Str(data_key="project_name")
    content = fields.Str(data_key="content")


class SearchResponseSchema(Schema):
    """Search Request Schema"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    documents = fields.List(fields.Nested(DocumentSchema), data_key="documents")


class SearchRequestSchema(Schema):
    """Search Request Schema"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    question = fields.Str(data_key="question")
