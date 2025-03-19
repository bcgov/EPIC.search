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

from services.search_service import SearchService

from .apihelper import Api as ApiHelper
from flask import Response
from marshmallow import EXCLUDE, Schema, fields

import json


class SearchRequestSchema(Schema):
    """Search Request Schema"""

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""

        unknown = EXCLUDE

    query = fields.Str(data_key="query")


API = Namespace("vector-search", description="Endpoints for Search")
"""Custom exception messages
"""

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchRequestSchema(), "Vector Search"
)


@API.route("", methods=["POST", "OPTIONS"])
class Search(Resource):
    """Resource for search."""

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Query Vector Database")
    @API.expect(search_request_model)
    @API.response(400, "Bad Request")
    def post():
        """Search"""
        request_data = SearchRequestSchema().load(API.payload)
        documents = SearchService.get_documents_by_query(request_data["query"])
        return Response(
            json.dumps(documents), status=HTTPStatus.OK, mimetype="application/json"
        )
