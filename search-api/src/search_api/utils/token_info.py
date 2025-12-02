from flask import g

def get_user_id():
    """Return the user ID (sub) from JWT token, or None if not available."""
    token_info = getattr(g, "jwt_oidc_token_info", {})
    return token_info.get("sub")
