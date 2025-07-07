"""Search schemas for request and response validation.

This module contains Marshmallow schemas for validating and serializing
search-related API requests and responses, including document structures
and search parameters.
"""

from marshmallow import EXCLUDE, Schema, fields


class DocumentSchema(Schema):
    """Schema for document objects returned in search results.
    
    Defines the structure and validation for individual document items
    that are returned as part of search responses from the vector search API.
    """

    document_id = fields.Str(data_key="document_id", metadata={"description": "Unique identifier for the document"})
    document_type = fields.Str(data_key="document_type", metadata={"description": "Type/category of the document"})
    document_name = fields.Str(data_key="document_name", metadata={"description": "Original name of the document"})
    document_saved_name = fields.Str(data_key="document_saved_name", metadata={"description": "Saved/processed name of the document"})
    page_number = fields.Str(data_key="page_number", metadata={"description": "Page number within the document where content was found"})
    project_id = fields.Str(data_key="project_id", metadata={"description": "ID of the project this document belongs to"})
    project_name = fields.Str(data_key="project_name", metadata={"description": "Name of the project this document belongs to"})
    content = fields.Str(data_key="content", metadata={"description": "Relevant content/text extracted from the document"})
    s3_key = fields.Str(data_key="s3_key", metadata={"description": "S3 storage key for the document file"})


class SearchResponseSchema(Schema):
    """Schema for search API response validation.
    
    Defines the structure for responses returned by the search endpoints,
    containing the list of relevant documents found by the search operation.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    documents = fields.List(
        fields.Nested(DocumentSchema), 
        data_key="documents",
        metadata={"description": "List of documents found by the search operation"}
    )


class SearchRequestSchema(Schema):
    """Schema for search API request validation.
    
    Validates incoming search requests, ensuring required fields are present
    and optional parameters are properly formatted for the search operation.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    question = fields.Str(
        data_key="question", 
        required=True,
        metadata={"description": "The search query/question to find relevant documents for"}
    )
    projectIds = fields.List(
        fields.Str(), 
        data_key="projectIds", 
        required=False, 
        allow_none=True,
        metadata={"description": "Optional list of project IDs to filter search results. If not provided, searches across all projects."}
    )
