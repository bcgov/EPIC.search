"""MCP Server for EPIC Search Tools.

This server exposes the vector search API capabilities as MCP tools
that can be used by LLM agents for intelligent document search and analysis.
"""

import asyncio
import json
import os
import sys
from typing import Any, List
import httpx
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path to import mcp
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Tool, TextContent
from .tools.search_tools import SearchTools
from .tools.stats_tools import StatsTools

class EPICSearchMCPServer:
    """MCP Server for EPIC Search API tools."""
    
    def __init__(self):
        """Initialize the MCP server with search and stats tools."""
        # Load configuration from environment
        self.server_name = os.getenv("MCP_SERVER_NAME", "epic-search-tools")
        self.vector_api_base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.api_timeout = float(os.getenv("API_TIMEOUT", "300.0"))
        
        # Initialize server
        self.server = Server(self.server_name)
        self.http_client = httpx.AsyncClient(timeout=self.api_timeout)
        
        # Initialize tool handlers
        self.search_tools = SearchTools(self.http_client, self.vector_api_base_url)
        self.stats_tools = StatsTools(self.http_client, self.vector_api_base_url)
        
        # Set up logging
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Set up MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List all available tools."""
            tools = []
            tools.extend(self.search_tools.get_tools())
            tools.extend(self.stats_tools.get_tools())
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls from the LLM agent."""
            self.logger.info(f"Tool called: {name} with arguments: {arguments}")
            
            try:
                # Route to appropriate tool handler
                search_tools = [
                    "vector_search", "find_similar_documents", "agentic_search", 
                    "get_available_projects", "get_available_document_types", "get_document_type_details",
                    "get_search_strategies", "get_inference_options", "get_api_capabilities",
                    "document_similarity_search", "suggest_filters"
                ]
                if name.startswith("search_") or name in search_tools:
                    result = await self.search_tools.handle_tool_call(name, arguments)
                elif name.startswith("stats_") or name.startswith("get_"):
                    result = await self.stats_tools.handle_tool_call(name, arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # Format result as MCP TextContent
                result_text = json.dumps(result, indent=2, default=str)
                return [TextContent(type="text", text=result_text)]
                
            except Exception as e:
                self.logger.error(f"Error executing tool {name}: {str(e)}")
                error_result = {
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments
                }
                return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    async def run(self):
        """Run the MCP server."""
        try:
            self.logger.info(f"Starting EPIC Search MCP Server")
            self.logger.info(f"Server Name: {self.server_name}")
            self.logger.info(f"Vector API URL: {self.vector_api_base_url}")
            self.logger.info(f"API Timeout: {self.api_timeout}s")
            self.logger.info(f"Log Level: {self.log_level}")
            self.logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
            await self.server.run()
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            await self.http_client.aclose()

async def main():
    """Main entry point for the MCP server."""
    server = EPICSearchMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
