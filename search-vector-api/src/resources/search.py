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

"""API endpoints for managing search operations with vector-based similarity and keyword-based search.

This module provides REST API endpoints for searching documents using semantic vector search,
keyword-based search, or a combination of both (hybrid search). It utilizes embeddings
generated from sentence transformers and PostgreSQL with pgvector extension.
"""

from http import HTTPStatus

from flask_restx import Namespace, Resource

from services.search_service import SearchService

from .apihelper import Api as ApiHelper
from flask import Response
from marshmallow import EXCLUDE, Schema, fields

import json


class SearchRequestSchema(Schema):
    """Schema for validating search API requests.
    
    Contains the query parameter that users will provide when searching documents.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    query = fields.Str(data_key="query", required=True)


API = Namespace("vector-search", description="Endpoints for semantic and keyword vector search operations")

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchRequestSchema(), "Vector Search Request"
)


@API.route("", methods=["POST", "OPTIONS"])
class Search(Resource):
    """Resource for performing vector and keyword-based document searches.
    
    Exposes endpoints for searching documents using vector embeddings for semantic similarity
    and keyword matching for traditional search capabilities.
    """

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Query the vector database for semantically similar documents")
    @API.expect(search_request_model)
    @API.response(400, "Bad Request")
    @API.response(200, "Search successful")
    def post():
        """Perform a search operation against the vector database.
        
        Takes a query string, processes it using embedding models, and returns
        relevant documents ranked by their similarity to the query. The search
        combines semantic vector search with keyword-based search and uses a 
        cross-encoder model to re-rank results for maximum relevance.
        
        Returns:
            Response: JSON containing matched documents and metadata
        """
        request_data = SearchRequestSchema().load(API.payload)
        documents = SearchService.get_documents_by_query(request_data["query"])
        return Response(
            json.dumps(documents), status=HTTPStatus.OK, mimetype="application/json"
        )
