#!/usr/bin/env python3
"""
EPIC Search MCP Server - Standalone Testing Version

This is a simple standalone server for manual testing and debugging.
Run this directly to test MCP protocol interactions.
"""

import json
import sys
import logging

# Set up logging for standalone mode
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Simple standalone MCP server for testing."""
    logger.info("🔧 EPIC Search MCP Server - Standalone Test Mode")
    logger.info("💡 This server is for testing only. Use mcp_server.py for production.")
    logger.info("📝 Send JSON-RPC requests via stdin...")
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                method = request.get("method")
                request_id = request.get("id")
                
                logger.info(f"📨 Received: {method} (ID: {request_id})")
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {"listChanged": False}},
                            "serverInfo": {"name": "epic-search-standalone", "version": "1.0.0"}
                        }
                    }
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [
                                {
                                    "name": "test_echo",
                                    "description": "Simple echo test for standalone mode",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string", "description": "Message to echo"}
                                        },
                                        "required": ["message"]
                                    }
                                }
                            ]
                        }
                    }
                elif method == "tools/call":
                    params = request.get("params", {})
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    if tool_name == "test_echo":
                        message = arguments.get("message", "No message")
                        result = {
                            "echoed": message,
                            "mode": "standalone_test",
                            "status": "working"
                        }
                        
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
                                "message": "Unknown tool in standalone mode",
                                "data": f"Tool: {tool_name}"
                            }
                        }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                            "data": f"Method: {method}"
                        }
                    }
                
                # Send response
                response_json = json.dumps(response)
                sys.stdout.write(response_json + "\n")
                sys.stdout.flush()
                logger.info(f"📤 Sent response for {method}")
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error", "data": str(e)}
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        logger.info("🛑 Standalone server stopped")
    except Exception as e:
        logger.error(f"💥 Error: {e}")
    
    logger.info("👋 Standalone server shutdown")

if __name__ == "__main__":
    main()
