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
"""Bring in the common JWT Manager."""
import logging
from functools import wraps
from http import HTTPStatus

from flask import g, request, current_app
from flask_jwt_oidc import JwtManager
from flask_jwt_oidc.exceptions import AuthError

jwt = (
    JwtManager()
)  # pylint: disable=invalid-name; lower case name as used by convention in most Flask apps


class Auth:  # pylint: disable=too-few-public-methods
    """Extending JwtManager to include additional functionalities."""

    @classmethod
    def require(cls, f):
        """Validate the Bearer Token."""

        @wraps(f)
        def decorated(*args, **kwargs):
            # Log authentication attempt for debugging
            auth_header = request.headers.get("Authorization", None)
            logging.info(f"=== Authentication Debug ===")
            logging.info(f"Authorization Header: {auth_header[:50] + '...' if auth_header and len(auth_header) > 50 else auth_header}")
            logging.info(f"Request Method: {request.method}")
            logging.info(f"Request Path: {request.path}")
            
            try:
                # Apply JWT validation
                @jwt.requires_auth
                @wraps(f)
                def jwt_decorated(*inner_args, **inner_kwargs):
                    g.authorization_header = request.headers.get("Authorization", None)
                    g.token_info = g.jwt_oidc_token_info
                    return f(*inner_args, **inner_kwargs)
                
                return jwt_decorated(*args, **kwargs)
            except AuthError as e:
                logging.warning(f"JWT Authentication failed: {e.error}")
                # Return proper 401 response as raw dict (Flask-RESTX will serialize it)
                return {
                    "error": "Unauthorized",
                    "message": "Authentication required",
                    "code": e.error.get('code', 'authorization_required')
                }, HTTPStatus.UNAUTHORIZED
            except Exception as e:
                logging.error(f"Unexpected auth error: {e}")
                raise

        return decorated


    @classmethod
    def requires_epic_search_role(cls, allowed_roles=None):
        """
        Decorator to allow only users with specified Epic Search roles.

        Args:
            allowed_roles (list[str], optional): List of allowed roles. Defaults to ["viewer", "admin"].
        """
        if allowed_roles is None:
            allowed_roles = ["viewer", "admin"]

        def decorator(f):
            @cls.require  # Ensure user is authenticated first
            @wraps(f)
            def wrapper(*args, **kwargs):
                token_info = g.token_info or {}
                app_name = current_app.config.get("JWT_OIDC_AUDIENCE")
                roles = token_info.get("resource_access", {}).get(app_name, {}).get("roles", [])

                if not any(role in allowed_roles for role in roles):
                    return {
                        "error": "Forbidden",
                        "message": "User does not have permission to access this endpoint"
                    }, HTTPStatus.FORBIDDEN

                return f(*args, **kwargs)
            return wrapper
        return decorator

auth = (
    Auth()
)
