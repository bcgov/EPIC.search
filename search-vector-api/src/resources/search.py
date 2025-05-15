# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""API endpoints for vector and keyword-based document search operations.

This module provides REST API endpoints for searching documents using multiple search strategies:
1. Semantic vector search using document embeddings for meaning-based matches
2. Keyword-based search for traditional text matching
3. Hybrid search combining both approaches for optimal results

The implementation uses Flask-RESTx for API definition with Swagger documentation,
Marshmallow for request validation, and delegates search logic to the SearchService.
Results include both matched documents and detailed performance metrics for each
search stage in the pipeline.
"""

from http import HTTPStatus

from flask_restx import Namespace, Resource
from flask import Response
from marshmallow import EXCLUDE, Schema, fields

import json

from services.search_service import SearchService
from .apihelper import Api as ApiHelper


class SearchRequestSchema(Schema):
    """Schema for validating and deserializing search API requests.
    
    Defines the structure and validation rules for incoming search requests,
    ensuring that required fields are present and properly formatted.
    
    Attributes:
        query: The required search query string provided by the user
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    query = fields.Str(data_key="query", required=True, 
                      metadata={"description": "Search query text to find relevant documents"})


API = Namespace("vector-search", description="Endpoints for semantic and keyword vector search operations")

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchRequestSchema(), "Vector Search Request"
)


@API.route("", methods=["POST", "OPTIONS"])
class Search(Resource):
    """REST resource for hybrid document search operations.
    
    This resource exposes endpoints for searching documents using a combination
    of semantic vector similarity and keyword-based text matching. The search
    results are re-ranked using a cross-encoder model to maximize relevance.
    
    The implementation prioritizes search quality through a multi-stage
    pipeline while also providing detailed performance metrics for monitoring.
    """

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Query the vector database for semantically similar documents")
    @API.expect(search_request_model)
    @API.response(400, "Bad Request")
    @API.response(200, "Search successful")
    def post():
        """Perform a hybrid search operation against the document database.
        
        This endpoint takes a natural language query string and returns relevant
        documents ranked by their similarity to the query. The search process:
        
        1. Extracts keywords and generates embeddings from the query
        2. Performs parallel keyword and semantic vector searches
        3. Combines and deduplicates the results
        4. Re-ranks the combined results using a cross-encoder model
        5. Returns the top N most relevant documents with search metrics
        
        Returns:
            Response: JSON containing matched documents and detailed search metrics
                     for each stage of the search pipeline
        """
        request_data = SearchRequestSchema().load(API.payload)
        documents = SearchService.get_documents_by_query(request_data["query"])
        return Response(
            json.dumps(documents), status=HTTPStatus.OK, mimetype="application/json"
        )
