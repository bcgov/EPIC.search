#!/usr/bin/env python3
"""
EPIC Search MCP Server - Production Version

This is the main MCP server that the Flask API uses for agentic workflows.
It handles JSON-RPC requests manually to avoid MCP library compatibility issues.
"""

import json
import sys
import logging
import os
import asyncio
import httpx
from typing import Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the tools from our tools folder
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from tools.search_tools import SearchTools

# Global tools instances
search_tools = None

def send_response(response_data):
    """Send a JSON-RPC response to stdout."""
    try:
        response_json = json.dumps(response_data, ensure_ascii=False, separators=(',', ':'))
        sys.stdout.write(response_json + "\n")
        sys.stdout.flush()
        logger.debug(f"Response sent: {response_json}")
    except Exception as e:
        logger.error(f"Error sending response: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        }
        error_json = json.dumps(error_response)
        sys.stdout.write(error_json + "\n")
        sys.stdout.flush()

def handle_initialize(request_id, params):
    """Handle the initialize request."""
    logger.info("Initializing EPIC Search MCP Server")
    
    try:
        client_info = params.get("clientInfo", {})
        protocol_version = params.get("protocolVersion", "unknown")
        
        logger.info(f"Client: {client_info.get('name', 'unknown')} v{client_info.get('version', 'unknown')}")
        logger.info(f"Protocol version: {protocol_version}")
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": False
                    },
                    "resources": {
                        "subscribe": False,
                        "listChanged": False
                    },
                    "prompts": {
                        "listChanged": False
                    },
                    "logging": {}
                },
                "serverInfo": {
                    "name": "epic-search-mcp",
                    "version": "1.0.0"
                },
                "instructions": "EPIC Search MCP Server - Provides intelligent document search tools"
            }
        }
        
        send_response(response)
        logger.info("✅ Initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": "Initialization failed",
                "data": str(e)
            }
        }
        send_response(error_response)

def handle_tools_list(request_id, params):
    """Handle tools/list request - return available tools."""
    logger.info("Listing available MCP tools")
    
    try:
        # Initialize tools if needed
        global search_tools
        if search_tools is None:
            # Use the same environment variable as VectorSearchClient
            vector_api_base_url = os.getenv('VECTOR_SEARCH_API_URL', 'http://localhost:8080/api')
            
            # Create HTTP client for tools
            http_client = httpx.AsyncClient(timeout=30.0)
            search_tools = SearchTools(http_client, vector_api_base_url)            
        
        # Define the core tools we want to expose for the full agentic workflow
        core_tools = [
            {
                "name": "echo_test",
                "description": "Simple echo test to verify MCP server connectivity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Message to echo back"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "check_query_relevance",
                "description": "Check if a query is relevant to EAO (Environmental Assessment Office) and environmental assessments",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's query to check for EAO relevance"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about the query"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "suggest_filters",
                "description": "Analyze a query and suggest optimal project and document type filters using AI",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's search query to analyze for filter suggestions"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about what the user is looking for"
                        },
                        "confidence_threshold": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.6,
                            "description": "Minimum confidence level for filter suggestions"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "suggest_search_strategy",
                "description": "Analyze a query and recommend the optimal search strategy based on query characteristics",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's search query to analyze for strategy recommendation"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about the search"
                        },
                        "user_intent": {
                            "type": "string",
                            "enum": ["find_documents", "explore_topic", "get_overview", "specific_lookup", "find_similar"],
                            "default": "find_documents",
                            "description": "The user's intent to help optimize strategy selection"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "vector_search",
                "description": "Perform vector similarity search through documents with advanced parameters (the normal search endpoint)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "The search query to find relevant documents"
                        },
                        "project_ids": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "Optional list of project IDs to filter by (from suggest_filters)"
                        },
                        "document_type_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of document type IDs to filter by (from suggest_filters)"
                        },
                        "inference": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["PROJECT", "DOCUMENTTYPE"]
                            },
                            "description": "Optional inference types to enable for intelligent filtering"
                        },
                        "ranking": {
                            "type": "object",
                            "properties": {
                                "minScore": {"type": "number", "description": "Minimum relevance score threshold"},
                                "topN": {"type": "integer", "description": "Maximum number of results to return"}
                            },
                            "description": "Optional ranking configuration"
                        },
                        "search_strategy": {
                            "type": "string",
                            "enum": [
                                "HYBRID_SEMANTIC_FALLBACK",
                                "HYBRID_KEYWORD_FALLBACK", 
                                "SEMANTIC_ONLY",
                                "KEYWORD_ONLY",
                                "HYBRID_PARALLEL"
                            ],
                            "description": "Search strategy to use (default: HYBRID_SEMANTIC_FALLBACK)"
                        }
                    },
                    "required": ["query"]
                }
            }
        ]
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": core_tools
            }
        }
        
        send_response(response)
        logger.info(f"✅ Listed {len(core_tools)} core tools successfully")
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": "Internal error listing tools",
                "data": str(e)
            }
        }
        send_response(error_response)

def handle_tools_call(request_id, params):
    """Handle tools/call request - execute the requested tool."""
    logger.info("Executing tool call")
    
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    logger.info(f"Tool: {tool_name}, Args: {arguments}")
    
    try:
        if tool_name == "echo_test":
            # Simple echo test - synchronous
            message = arguments.get("message", "No message provided")
            result_data = {
                "success": True,
                "echoed_message": message,
                "server": "EPIC Search MCP Server",
                "tool": "echo_test",
                "timestamp": str(os.times().elapsed)
            }
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result_data, indent=2)
                        }
                    ]
                }
            }
            
        elif tool_name in ["check_query_relevance", "suggest_filters", "suggest_search_strategy", "vector_search"]:
            # These tools require async execution
            result = asyncio.run(execute_async_tool(tool_name, arguments))
            
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
            
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found",
                    "data": f"Unknown tool: {tool_name}"
                }
            }
        
        send_response(response)
        logger.info(f"✅ Tool {tool_name} executed successfully")
        
    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}")
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Tool execution failed: {tool_name}",
                "data": str(e)
            }
        }
        send_response(error_response)

async def execute_async_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute async tool calls using the tools from the tools folder."""
    global search_tools
    
    # Ensure search_tools is initialized
    if search_tools is None:
        vector_api_base_url = os.getenv('VECTOR_SEARCH_API_URL', 'http://localhost:8080/api')
        http_client = httpx.AsyncClient(timeout=30.0)
        search_tools = SearchTools(http_client, vector_api_base_url)
    
    # Delegate to the appropriate tool handler
    try:
        if tool_name == "check_query_relevance":
            return await search_tools._check_query_relevance(arguments)
        elif tool_name == "suggest_filters":
            return await search_tools._suggest_filters(arguments)
        elif tool_name == "suggest_search_strategy":
            return await search_tools._suggest_search_strategy(arguments)
        elif tool_name == "vector_search":
            return await search_tools._vector_search(arguments)
        else:
            raise ValueError(f"Unknown async tool: {tool_name}")
            
    except Exception as e:
        logger.error(f"Async tool {tool_name} error: {e}")
        return {
            "tool": tool_name,
            "error": str(e),
            "arguments": arguments
        }

def main():
    """Main server loop - listen for JSON-RPC requests on stdin."""
    logger.info("🚀 Starting EPIC Search MCP Server (Production)")
    logger.info("📝 Listening for JSON-RPC requests on stdin...")
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                method = request.get("method")
                request_id = request.get("id")
                params = request.get("params", {})
                
                logger.debug(f"Request: {method} (ID: {request_id})")
                
                if method == "initialize":
                    handle_initialize(request_id, params)
                elif method == "tools/list":
                    handle_tools_list(request_id, params)
                elif method == "tools/call":
                    handle_tools_call(request_id, params)
                else:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                            "data": f"Unknown method: {method}"
                        }
                    }
                    send_response(error_response)
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                        "data": str(e)
                    }
                }
                send_response(error_response)
                
    except KeyboardInterrupt:
        logger.info("🛑 Server interrupted")
    except Exception as e:
        logger.error(f"💥 Server error: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("👋 EPIC Search MCP Server shutdown")

if __name__ == "__main__":
    main()
