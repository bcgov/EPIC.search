"""
MCP Client for Your API
=======================

This client allows your API to communicate with the MCP server via subprocess.
Your API uses this to send queries to the MCP server and get intelligent responses.

Usage:
    client = MCPClient()
    result = await client.call_tool("vector_search", {"query": "environmental impact"})
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List
import logging

class MCPClient:
    """Client to communicate with MCP server via subprocess."""
    
    def __init__(self, mcp_server_path: str = None, vector_api_url: str = None):
        """
        Initialize MCP client.
        
        Args:
            mcp_server_path: Path to the MCP server main.py (optional)
            vector_api_url: Vector API URL to pass to MCP server (optional)
        """
        self.logger = logging.getLogger(__name__)
        
        # Default to the main.py in this repo
        if mcp_server_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.mcp_server_path = os.path.join(current_dir, "main.py")
        else:
            self.mcp_server_path = mcp_server_path
            
        self.vector_api_url = vector_api_url or "http://localhost:8080/api"
        self.process = None
        
    async def start(self):
        """Start the MCP server subprocess."""
        try:
            env = os.environ.copy()
            env["VECTOR_SEARCH_API_URL"] = self.vector_api_url
            env["LOG_LEVEL"] = "INFO"
            env["ENVIRONMENT"] = "development"
            
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.mcp_server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            self.logger.info(f"Started MCP server process (PID: {self.process.pid})")
            
            # Initialize the MCP connection
            await self._send_initialize()
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def _send_initialize(self):
        """Send MCP initialization message."""
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "EPIC Search API Client",
                    "version": "1.0.0"
                }
            }
        }
        
        await self._send_message(init_message)
        response = await self._receive_message()
        
        if "error" in response:
            raise Exception(f"MCP initialization failed: {response['error']}")
            
        self.logger.info("MCP server initialized successfully")
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send a JSON-RPC message to the MCP server."""
        if not self.process:
            raise Exception("MCP server not started")
            
        message_str = json.dumps(message) + "\n"
        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()
        
    async def _receive_message(self) -> Dict[str, Any]:
        """Receive a JSON-RPC message from the MCP server."""
        if not self.process:
            raise Exception("MCP server not started")
            
        line = await self.process.stdout.readline()
        if not line:
            raise Exception("MCP server connection closed")
            
        try:
            return json.loads(line.decode().strip())
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse MCP response: {line.decode()}")
            raise Exception(f"Invalid JSON response from MCP server: {e}")
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP server."""
        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        await self._send_message(message)
        response = await self._receive_message()
        
        if "error" in response:
            raise Exception(f"Failed to list tools: {response['error']}")
            
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Call a specific MCP tool.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        if arguments is None:
            arguments = {}
            
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        await self._send_message(message)
        response = await self._receive_message()
        
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
            
        # Extract the actual result from MCP response
        result = response.get("result", {})
        if "content" in result and isinstance(result["content"], list):
            # Parse the text content from MCP response
            for content in result["content"]:
                if content.get("type") == "text":
                    try:
                        return json.loads(content["text"])
                    except json.JSONDecodeError:
                        return {"text": content["text"]}
        
        return result
    
    async def intelligent_search(self, query: str, context: str = None) -> Dict[str, Any]:
        """
        Perform an intelligent search using MCP tools.
        
        This is a high-level method that uses multiple MCP tools to:
        1. Analyze the query
        2. Get filter suggestions  
        3. Execute the search
        4. Return enhanced results
        """
        try:
            # First, try to get filter suggestions
            try:
                filter_result = await self.call_tool("suggest_filters", {
                    "query": query,
                    "context": context
                })
                self.logger.info(f"Filter suggestions: {filter_result}")
            except Exception as e:
                self.logger.warning(f"Filter suggestion failed: {e}")
                filter_result = None
            
            # Execute the search with or without filters
            search_args = {"query": query}
            if filter_result and "recommended_filters" in filter_result:
                filters = filter_result["recommended_filters"]
                if "project_ids" in filters:
                    search_args["project_ids"] = filters["project_ids"]
                if "document_types" in filters:
                    search_args["document_types"] = filters["document_types"]
            
            # Execute the main search
            search_result = await self.call_tool("vector_search", search_args)
            
            return {
                "query": query,
                "search_result": search_result,
                "filter_suggestions": filter_result,
                "enhanced": True
            }
            
        except Exception as e:
            self.logger.error(f"Intelligent search failed: {e}")
            # Fallback to basic search
            try:
                search_result = await self.call_tool("vector_search", {"query": query})
                return {
                    "query": query,
                    "search_result": search_result,
                    "enhanced": False,
                    "fallback": True
                }
            except Exception as fallback_error:
                raise Exception(f"Both intelligent and fallback search failed: {e}, {fallback_error}")
    
    async def stop(self):
        """Stop the MCP server subprocess."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            
            self.logger.info("MCP server stopped")
            self.process = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


# Example usage for your API
async def example_usage():
    """Example of how your API would use this MCP client."""
    
    async with MCPClient(vector_api_url="http://localhost:8080/api") as client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool['name'] for tool in tools]}")
        
        # Perform intelligent search
        result = await client.intelligent_search(
            query="environmental impact assessment coastal development",
            context="Looking for EIA documents related to coastal projects"
        )
        
        print(f"Search result: {result}")
        
        # Call specific tools
        projects = await client.call_tool("get_available_projects")
        print(f"Available projects: {projects}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
