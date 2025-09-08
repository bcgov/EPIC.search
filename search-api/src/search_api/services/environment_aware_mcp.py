"""Environment-aware MCP client that adapts to deployment context.

This service automatically detects the deployment environment and chooses
the appropriate MCP communication method:
- Local development: Subprocess MCP server
- Azure/Container: Direct integration or HTTP-based MCP server
"""

import os
import logging
from typing import Dict, Any, Optional
from flask import current_app


def is_azure_app_service() -> bool:
    """Detect if running in Azure App Service."""
    return bool(os.getenv('WEBSITE_SITE_NAME') or os.getenv('APPSETTING_WEBSITE_SITE_NAME'))


def is_container_environment() -> bool:
    """Detect if running in a container environment."""
    return (
        os.path.exists('/.dockerenv') or 
        os.getenv('KUBERNETES_SERVICE_HOST') is not None or
        os.getenv('CONTAINER_NAME') is not None or
        is_azure_app_service()
    )


class EnvironmentAwareMCPClient:
    """MCP client that adapts to the deployment environment."""
    
    def __init__(self):
        """Initialize the environment-aware MCP client."""
        self.logger = logging.getLogger(__name__)
        self.is_container = is_container_environment()
        self.is_azure = is_azure_app_service()
        
        # Choose the appropriate MCP implementation
        if self.is_container:
            self.logger.info("Container environment detected - using direct MCP integration")
            self._use_direct_mode = True
        else:
            self.logger.info("Local environment detected - using subprocess MCP server")
            self._use_direct_mode = False
        
        self._direct_service = None
        self._subprocess_client = None
        
    def _get_direct_service(self):
        """Get the direct MCP service."""
        if self._direct_service is None:
            try:
                from .mcp_direct_service import get_mcp_direct_service
                self._direct_service = get_mcp_direct_service()
            except ImportError as e:
                self.logger.error(f"Direct MCP service not available: {e}")
                raise Exception("Direct MCP mode not available in container environment")
        return self._direct_service
    
    def _get_subprocess_client(self):
        """Get the subprocess MCP client."""
        if self._subprocess_client is None:
            try:
                from ..clients.mcp_client import call_mcp_tool_with_retry
                self._subprocess_client = call_mcp_tool_with_retry
            except ImportError as e:
                self.logger.error(f"Subprocess MCP client not available: {e}")
                raise Exception("Subprocess MCP mode not available")
        return self._subprocess_client
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool using the appropriate method for the environment."""
        try:
            if self._use_direct_mode:
                # Use direct integration for containers
                direct_service = self._get_direct_service()
                
                if tool_name == "suggest_filters":
                    return await direct_service.suggest_filters(
                        arguments.get("query", ""),
                        arguments.get("context")
                    )
                elif tool_name == "suggest_search_strategy":
                    return await direct_service.suggest_search_strategy(
                        arguments.get("query", ""),
                        arguments.get("context"),
                        arguments.get("user_intent")
                    )
                elif tool_name == "check_query_relevance":
                    return await direct_service.check_query_relevance(
                        arguments.get("query", ""),
                        arguments.get("context")
                    )
                else:
                    raise Exception(f"Tool '{tool_name}' not implemented in direct mode")
            else:
                # Use subprocess for local development
                subprocess_client = self._get_subprocess_client()
                return subprocess_client(tool_name, arguments)
                
        except Exception as e:
            self.logger.error(f"Error calling MCP tool '{tool_name}': {str(e)}")
            raise
    
    def close(self):
        """Clean up resources."""
        if self._direct_service:
            self._direct_service.close()
            self._direct_service = None


# Global instance
_environment_aware_client = None


def get_environment_aware_mcp_client() -> EnvironmentAwareMCPClient:
    """Get or create the global environment-aware MCP client."""
    global _environment_aware_client
    
    if _environment_aware_client is None:
        _environment_aware_client = EnvironmentAwareMCPClient()
    
    return _environment_aware_client


def cleanup_environment_aware_client():
    """Clean up the environment-aware client."""
    global _environment_aware_client
    
    if _environment_aware_client:
        _environment_aware_client.close()
        _environment_aware_client = None
