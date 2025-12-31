"""Search schemas for request and response validation.

This module contains Marshmallow schemas for validating and serializing
search-related API requests and responses, including document structures
and search parameters.

The search request schema supports optional filtering parameters for enhanced
search capabilities while maintaining backward compatibility.
"""

from marshmallow import EXCLUDE, Schema, fields, validate


class UserLocationSchema(Schema):
    """Schema for user location information in search requests.
    
    Defines the structure for optional location data that can be provided
    to enhance search results with geographic context.
    """
    
    class Meta:
        unknown = EXCLUDE
    
    latitude = fields.Float(
        data_key="latitude",
        required=False,
        allow_none=True,
        metadata={"description": "Latitude coordinate of the user's location"}
    )
    longitude = fields.Float(
        data_key="longitude", 
        required=False,
        allow_none=True,
        metadata={"description": "Longitude coordinate of the user's location"}
    )
    city = fields.Str(
        data_key="city",
        required=False,
        allow_none=True,
        metadata={"description": "City name of the user's location"}
    )
    region = fields.Str(
        data_key="region",
        required=False,
        allow_none=True,
        metadata={"description": "Region/state/province of the user's location"}
    )
    country = fields.Str(
        data_key="country",
        required=False,
        allow_none=True,
        metadata={"description": "Country of the user's location"}
    )
    timestamp = fields.Int(
        data_key="timestamp",
        required=False,
        allow_none=True,
        metadata={"description": "Unix timestamp when the location was captured"}
    )


class RankingSchema(Schema):
    """Schema for ranking configuration in search requests.
    
    Defines the structure for optional ranking parameters that control
    result filtering and limiting in the vector search operation.
    """
    
    class Meta:
        unknown = EXCLUDE
    
    minScore = fields.Float(
        data_key="minScore",
        required=False,
        allow_none=True,
        metadata={"description": "Minimum relevance score threshold for filtering results (default: -8.0)"}
    )
    topN = fields.Int(
        data_key="topN", 
        required=False,
        allow_none=True,
        metadata={"description": "Maximum number of results to return after ranking (default: 10)"}
    )


class DocumentSchema(Schema):
    """Schema for document objects returned in search results.
    
    Defines the structure and validation for individual document items
    that are returned as part of search responses from the vector search API.
    Handles both document and document_chunks response formats.
    """

    document_id = fields.Str(data_key="document_id", metadata={"description": "Unique identifier for the document"})
    document_type = fields.Str(data_key="document_type", metadata={"description": "Type/category of the document"})
    document_name = fields.Str(data_key="document_name", metadata={"description": "Original name of the document"})
    document_saved_name = fields.Str(data_key="document_saved_name", metadata={"description": "Saved/processed name of the document"})
    document_date = fields.Str(data_key="document_date", metadata={"description": "Date of the document"})
    page_number = fields.Str(data_key="page_number", metadata={"description": "Page number within the document where content was found"})
    project_id = fields.Str(data_key="project_id", metadata={"description": "ID of the project this document belongs to"})
    project_name = fields.Str(data_key="project_name", metadata={"description": "Name of the project this document belongs to"})
    proponent_name = fields.Str(data_key="proponent_name", metadata={"description": "Name of the project proponent"})
    content = fields.Str(data_key="content", metadata={"description": "Relevant content/text extracted from the document"})
    s3_key = fields.Str(data_key="s3_key", metadata={"description": "S3 storage key for the document file"})
    relevance_score = fields.Float(data_key="relevance_score", metadata={"description": "Relevance score for this document/chunk"})
    search_mode = fields.Str(data_key="search_mode", metadata={"description": "Search mode used to find this result"})


class SearchResponseSchema(Schema):
    """Schema for search API response validation.
    
    Defines the structure for responses returned by the search endpoints.
    The response can contain either 'documents' (metadata-focused results) or 
    'document_chunks' (content-focused results) depending on the search type performed.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    documents = fields.List(
        fields.Nested(DocumentSchema), 
        data_key="documents",
        required=False,
        allow_none=True,
        metadata={"description": "List of documents found by the search operation (metadata-focused results)"}
    )
    
    document_chunks = fields.List(
        fields.Nested(DocumentSchema), 
        data_key="document_chunks",
        required=False,
        allow_none=True,
        metadata={"description": "List of document chunks found by the search operation (content-focused results)"}
    )


class SearchRequestSchema(Schema):
    """Schema for search API request validation.
    
    Validates incoming search requests, ensuring required fields are present
    and optional parameters are properly formatted for the search operation.
    
    Supports advanced search options including inference control, custom ranking,
    and search strategy selection for enhanced search capabilities.
    
    All parameters except 'query' are optional and maintain backward compatibility
    with existing API clients.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    query = fields.Str(
        data_key="query", 
        required=True,
        metadata={"description": "The search query to find relevant documents for"}
    )
    projectIds = fields.List(
        fields.Str(), 
        data_key="projectIds", 
        required=False, 
        allow_none=True,
        metadata={"description": "Optional list of project IDs to filter search results by. If not provided, searches across all projects."}
    )
    documentTypeIds = fields.List(
        fields.Str(), 
        data_key="documentTypeIds", 
        required=False, 
        allow_none=True,
        metadata={"description": "Optional list of document type IDs to filter search results by. If not provided, searches across all document types."}
    )
    inference = fields.List(
        fields.Str(), 
        data_key="inference", 
        required=False, 
        allow_none=True,
        metadata={"description": "Optional list of inference types to enable (e.g., ['PROJECT', 'DOCUMENTTYPE']). If not provided, uses the vector search API's default inference settings."}
    )
    ranking = fields.Nested(
        RankingSchema,
        data_key="ranking",
        required=False,
        allow_none=True,
        metadata={"description": "Optional ranking configuration object with keys like 'minScore' and 'topN'. If not provided, uses the vector search API's default ranking settings."}
    )
    searchStrategy = fields.Str(
        data_key="searchStrategy",
        required=False,
        allow_none=True,
        metadata={"description": "Optional search strategy to use. Available options: 'HYBRID_SEMANTIC_FALLBACK' (default), 'HYBRID_KEYWORD_FALLBACK', 'SEMANTIC_ONLY', 'KEYWORD_ONLY', 'HYBRID_PARALLEL'. If not provided, uses the vector search API's default strategy."}
    )
    mode = fields.Str(
        data_key="mode",
        required=False,
        allow_none=True,
        validate=validate.OneOf(["rag", "summary", "ai", "agent", "auto"]),
        load_default="rag",
        metadata={"description": "Processing mode: 'rag' for pure RAG search (default), 'summary' for RAG search with AI summarization, 'ai' for AI processing with parameter extraction and summarization, 'agent' for full agent processing including advanced reasoning, 'auto' for automatic mode selection based on query complexity. Controls the level of AI processing applied to the query."}
    )
    userLocation = fields.Nested(
        UserLocationSchema,
        data_key="userLocation",
        required=False,
        allow_none=True,
        metadata={"description": "User's physical geographic location from browser/device (NOT a search filter). Used to resolve 'near me' queries and provide local context. Example: {latitude: 48.4284, longitude: -123.3656, city: 'Victoria', region: 'British Columbia'}. Geographic search filters (e.g., 'projects in Vancouver') are automatically extracted from the query text in AI/agent modes."}
    )
    projectStatus = fields.Str(
        data_key="projectStatus",
        required=False,
        allow_none=True,
        metadata={"description": "Project status filter - 'recent', 'active', 'completed', 'historical'. Provides database-level status filtering."}
    )
    years = fields.List(
        fields.Int(),
        data_key="years",
        required=False,
        allow_none=True,
        metadata={"description": "List of years to filter by - [2023, 2024, 2025] for recent documents, [2015, 2016, 2017] for historical. Provides database-level temporal filtering."}
    )


class SimilaritySearchRequestSchema(Schema):
    """Schema for similarity search API request validation.
    Used for POST /api/search/document-similarity to find similar documents.
    """
    class Meta:
        unknown = EXCLUDE

    document_id = fields.Str(data_key="documentId", required=True, metadata={"description": "The source document ID to find similarities for."})
    project_ids = fields.List(
        fields.Str(),
        data_key="projectIds",
        required=False,
        allow_none=True,
        metadata={"description": "Optional list of project IDs to filter similar documents."}
    )
    limit = fields.Int(data_key="limit", required=False, allow_none=True, metadata={"description": "Maximum number of similar documents to return (default: 10)"})


class SimilarDocumentSchema(Schema):
    """Schema for individual similar document objects."""

    document_id = fields.Str()
    document_keywords = fields.List(fields.Str())
    document_tags = fields.List(fields.Str())
    document_headings = fields.List(fields.Str())
    project_id = fields.Str()
    similarity_score = fields.Float()
    created_at = fields.DateTime()


class SimilaritySearchMetricsSchema(Schema):
    """Schema for search metrics in similarity search responses."""

    embedding_retrieval_ms = fields.Float()
    similarity_search_ms = fields.Float()
    formatting_ms = fields.Float()
    total_search_ms = fields.Float()


class SimilaritySearchResponseSchema(Schema):
    """Schema for similarity search API response validation.
    
    Defines the structure for responses returned by the similarity search endpoint,
    containing the list of similar documents found and search metrics.
    """

    similar_documents = fields.List(fields.Nested(SimilarDocumentSchema))
    search_metrics = fields.Nested(SimilaritySearchMetricsSchema)


class FeedbackSchema(Schema):
    session_id = fields.Str(
        required=True,
        data_key="sessionId",
        metadata={"description": "Feedback session ID for the search query"}
    )
    feedback = fields.Str(
        required=False,
        validate=validate.OneOf(
            ["up", "down",]
        ),
        metadata={"description": "Overall feedback value"}
    )
    comments = fields.Str(
        required=False,
        metadata={"description": "Optional general comments from the user"}
    )

    summary_helpful = fields.Int(
        required=False,
        data_key="summaryHelpful",
        validate=validate.Range(min=1, max=5),
        metadata={"description": "How helpful the AI summary was (1-5)"}
    )

    summary_accurate = fields.Int(
        required=False,
        data_key="summaryAccurate",
        validate=validate.Range(min=1, max=5),
        metadata={"description": "How accurate the AI summary was (1-5)"}
    )

    doc_helpful = fields.Int(
        required=False,
        data_key="docHelpful",
        validate=validate.Range(min=1, max=5),
        metadata={"description": "How helpful the document search results were (1-5)"}
    )

    doc_accurate = fields.Int(
        required=False,
        data_key="docAccurate",
        validate=validate.Range(min=1, max=5),
        metadata={"description": "How accurate the document search results were (1-5)"}
    )

    summary_improvement = fields.Str(
        required=False,
        data_key="summaryImprovement",
        metadata={"description": "Suggestions to improve the AI summary"}
    )

    doc_improvement = fields.Str(
        required=False,
        data_key="docImprovement",
        metadata={"description": "Suggestions to improve document search results"}
    )
