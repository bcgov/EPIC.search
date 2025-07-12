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
"""API endpoints for managing an search resource."""

from http import HTTPStatus
from flask_restx import Namespace, Resource
from search_api.services.search_service import SearchService
from search_api.utils.util import cors_preflight
from search_api.schemas.search import SearchRequestSchema
from search_api.schemas.search import SimilaritySearchRequestSchema
from .apihelper import Api as ApiHelper
from flask import Response, current_app

import json

API = Namespace("search", description="Endpoints for Search")
"""Custom exception messages
"""

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchRequestSchema(), "Search"
)

similar_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SimilaritySearchRequestSchema(), "Search"
)

@cors_preflight("POST, OPTIONS")
@API.route("/query", methods=["POST", "OPTIONS"])
class Search(Resource):
    """Resource for search."""    
    @staticmethod
    #@auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Search Query")
    @API.expect(search_request_model)
    @API.response(400, "Bad Request")
    @API.response(500, "Internal Server Error")
    def post():
        """Search"""
        try:
            request_data = SearchRequestSchema().load(API.payload)
                        
            question = request_data.get("question", None)
            project_ids = request_data.get("projectIds", None)
            document_type_ids = request_data.get("documentTypeIds", None)
            inference = request_data.get("inference", None)
        
            documents = SearchService.get_documents_by_query(question, project_ids, document_type_ids, inference)
            return Response(json.dumps(documents), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            # Log the error internally            
            current_app.logger.error(f"Search error occurred: {str(e)}")
            # Return a generic error message
            error_response = {"error": "Internal server error occurred"}
            return Response(json.dumps(error_response), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')


@cors_preflight("POST, OPTIONS")
@API.route("/similar", methods=["POST", "OPTIONS"])
class SearchSimilar(Resource):
    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Find documents similar to a given document using document-level embeddings.")
    @API.expect(similar_request_model)
    @API.response(400, "Bad Request")
    @API.response(500, "Internal Server Error")
    def post():
        try:
            request_data = SimilaritySearchRequestSchema().load(API.payload)
            document_id = request_data.get("document_id")
            project_ids = request_data.get("projectIds", None)
            limit = request_data.get("limit", 10)
            result = SearchService.get_similar_documents(document_id, project_ids, limit)
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Search similar POST error: {str(e)}")
            return Response(json.dumps({"error": "Failed to get similar documents"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')
