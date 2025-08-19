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
"""API blueprint and namespace initialization for the Vector Search API.

This module defines and configures the Flask blueprints and API namespaces that form
the REST API structure of the application. It organizes endpoints into logical groups:

1. Main API Blueprint (/api/*)
   - Vector search endpoints for searching documents

2. Health Blueprint (/*)
   - Operational health endpoints for monitoring and status checks

The module uses Flask-RESTx namespaces to maintain separation of concerns between
different API resources while providing consistent documentation through Swagger.
"""

from flask import Blueprint

from .apihelper import Api

from .search import API as SEARCH_VECTOR_API, SIMILARITY_API as DOCUMENT_SIMILARITY_API
from .stats import API as STATS_API
from .tools import API as TOOLS_API
from .ops import API as OPS_API

__all__ = ("API_BLUEPRINT", "HEALTH_BLUEPRINT")

# Define URL prefixes for different endpoint groups
URL_PREFIX = "/api/"
API_BLUEPRINT = Blueprint("API", __name__, url_prefix=URL_PREFIX)


HEALTH_URL_PREFIX = "/"
HEALTH_BLUEPRINT = Blueprint("HEALTH", __name__, url_prefix=HEALTH_URL_PREFIX)

# Initialize API with Swagger documentation for the main API endpoints
API = Api(
    API_BLUEPRINT,
    title="VECTOR SEARCH API",
    version="1.0",
    description="Query Vector Database for documents using semantic and keyword search",
)

# Initialize API with Swagger documentation for the health endpoints
HEALTH = Api(
    HEALTH_BLUEPRINT,
    title="VECTOR HEALTH ENDPOINTS",
    version="1.0",
    description="Health and operational status endpoints for monitoring and diagnostics",
)

# Register namespaces with their respective API blueprints
API.add_namespace(SEARCH_VECTOR_API)
API.add_namespace(DOCUMENT_SIMILARITY_API)
API.add_namespace(STATS_API)
API.add_namespace(TOOLS_API)
HEALTH.add_namespace(OPS_API)
