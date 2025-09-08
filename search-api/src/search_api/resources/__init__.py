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
"""Exposes all of the resource endpoints mounted in Flask-Blueprint style.

Uses restplus namespaces to mount individual api endpoints into the service.

All services have 2 defaults sets of endpoints:
 - ops
 - meta
That are used to expose operational health information about the service, and meta information.
"""

from flask import Blueprint
from .apihelper import Api
from .search import API as SEARCH_API
from .ops import API as OPS_API
from .document import API as DOCUMENT_API
from .stats import API as STATS_API
from .tools import API as TOOLS_API

import logging
logger = logging.getLogger(__name__)
logger.info("Loading search-api resources module")
logger.info(f"DOCUMENT_API: {DOCUMENT_API}")
logger.info(f"DOCUMENT_API name: {DOCUMENT_API.name}")

__all__ = ("API_BLUEPRINT",)

URL_PREFIX = "/api"
API_BLUEPRINT = Blueprint("API", __name__, url_prefix=URL_PREFIX)

URL_PREFIX = "/"
HEALTH_BLUEPRINT = Blueprint("HEALTH", __name__, url_prefix=URL_PREFIX)

authorizations = {
    "Bearer Auth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": 'Add "Bearer " before your token',
    }
}

API = Api(
    API_BLUEPRINT,
    title="SEARCH API",
    version="1.0",
    description="The Core API for SEARCH",
    authorizations=authorizations,
)

HEALTH = Api(
    HEALTH_BLUEPRINT,
    title="HEALTH ENDPOINTS",
    version="1.0",
    description="Health Endpoints",
)

API.add_namespace(SEARCH_API)
API.add_namespace(DOCUMENT_API)
API.add_namespace(STATS_API)
API.add_namespace(TOOLS_API)
HEALTH.add_namespace(OPS_API)

logger.info("API namespaces registered:")
logger.info(f"- SEARCH_API: {SEARCH_API.name}")
logger.info(f"- DOCUMENT_API: {DOCUMENT_API.name}")
logger.info(f"- STATS_API: {STATS_API.name}")
logger.info(f"- TOOLS_API: {TOOLS_API.name}")
logger.info(f"- OPS_API: {OPS_API.name}")

# Log registered routes after the API object is fully configured
logger.info("API Blueprint configured successfully")
