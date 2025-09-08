"""Direct MCP tools integration service for Azure deployment.

This service provides direct access to MCP tools without subprocess communication,
making it suitable for containerized environments like Azure App Service.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from flask import current_app

# Add MCP server path to allow imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mcp_server'))

try:
    from tools.search_tools import SearchTools
    import httpx
    MCP_TOOLS_AVAILABLE = True
except ImportError as e:
    current_app.logger.warning(f"MCP tools not available for direct import: {e}")
    MCP_TOOLS_AVAILABLE = False


class MCPDirectService:
    """Service that provides MCP tools functionality without subprocess communication."""
    
    def __init__(self):
        """Initialize the direct MCP service."""
        self.logger = logging.getLogger(__name__)
        self._search_tools = None
        self._http_client = None
        
    def _ensure_initialized(self):
        """Ensure the MCP tools are initialized."""
        if not MCP_TOOLS_AVAILABLE:
            raise Exception("MCP tools are not available for direct import")
            
        if self._search_tools is None:
            # Get vector API URL from environment
            vector_api_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            
            # Create HTTP client
            self._http_client = httpx.AsyncClient(timeout=30.0)
            
            # Initialize search tools
            self._search_tools = SearchTools(self._http_client, vector_api_url)
            
            self.logger.info("MCP Direct Service initialized successfully")
    
    async def suggest_filters(self, query: str, context: str = None) -> Dict[str, Any]:
        """Direct call to suggest_filters tool."""
        try:
            self._ensure_initialized()
            
            # Prepare arguments
            args = {"query": query}
            if context:
                args["context"] = context
            
            # Call the tool directly
            result = await self._search_tools.suggest_filters(args)
            
            # Format result to match MCP protocol
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error in direct suggest_filters: {str(e)}")
            raise
    
    async def suggest_search_strategy(self, query: str, context: str = None, user_intent: str = None) -> Dict[str, Any]:
        """Direct call to suggest_search_strategy tool."""
        try:
            self._ensure_initialized()
            
            # Prepare arguments
            args = {"query": query}
            if context:
                args["context"] = context
            if user_intent:
                args["user_intent"] = user_intent
            
            # Call the tool directly
            result = await self._search_tools.suggest_search_strategy(args)
            
            # Format result to match MCP protocol
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": result
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error in direct suggest_search_strategy: {str(e)}")
            raise
    
    async def check_query_relevance(self, query: str, context: str = None) -> Dict[str, Any]:
        """Direct call to check_query_relevance tool."""
        try:
            self._ensure_initialized()
            
            # Prepare arguments
            args = {"query": query}
            if context:
                args["context"] = context
            
            # Call the tool directly
            result = await self._search_tools.check_query_relevance(args)
            
            # Format result to match MCP protocol
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result
                    }
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error in direct check_query_relevance: {str(e)}")
            raise
    
    def close(self):
        """Clean up resources."""
        if self._http_client:
            # Note: In a real async context, you'd await this
            # For now, we'll handle it synchronously
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If in async context, schedule cleanup
                    loop.create_task(self._http_client.aclose())
                else:
                    # If not in async context, create new loop
                    asyncio.run(self._http_client.aclose())
            except Exception as e:
                self.logger.warning(f"Error closing HTTP client: {e}")
            finally:
                self._http_client = None
        
        self._search_tools = None


# Global instance for Azure deployment
_mcp_direct_service = None


def get_mcp_direct_service() -> MCPDirectService:
    """Get or create the global MCP direct service instance."""
    global _mcp_direct_service
    
    if _mcp_direct_service is None:
        _mcp_direct_service = MCPDirectService()
    
    return _mcp_direct_service


def is_direct_mode_available() -> bool:
    """Check if direct MCP mode is available."""
    return MCP_TOOLS_AVAILABLE


def cleanup_mcp_direct_service():
    """Clean up the direct service."""
    global _mcp_direct_service
    
    if _mcp_direct_service:
        _mcp_direct_service.close()
        _mcp_direct_service = None
