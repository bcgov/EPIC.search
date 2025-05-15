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
from search_api.schemas.search import SearchRequestSchema, SearchResponseSchema
from search_api.exceptions import ResourceNotFoundError
from search_api.auth import auth
from .apihelper import Api as ApiHelper
from flask import jsonify,Response
import json

API = Namespace("search", description="Endpoints for Search")
"""Custom exception messages
"""

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchRequestSchema(), "Search"
)
document_list_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchResponseSchema(), "DocumentListItem"
)


@cors_preflight("GET, OPTIONS, POST")
@API.route("", methods=["POST", "GET", "OPTIONS"])
class Search(Resource):
    """Resource for search."""

    @staticmethod
    #@auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Search Query")
    @API.expect(search_request_model)
    # @API.response(code=201, model=document_list_model, description="SearchResult")
    @API.response(400, "Bad Request")
    def post():
        """Search"""
        request_data = SearchRequestSchema().load(API.payload)
       # print("request_data",request_data)
        documents = SearchService.get_documents_by_query(request_data["question"])
        print("documents", documents)
       # document_list_schema = SearchResponseSchema(many=True)
       # return document_list_schema.dump(documents), HTTPStatus.OK
        return Response(json.dumps(documents), status=HTTPStatus.OK, mimetype='application/json')

