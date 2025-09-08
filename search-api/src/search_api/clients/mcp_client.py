"""MCP (Model Context Protocol) Client for communicating with the MCP Server.

This module provides the orchestrator layer that communicates with the MCP server
running as a stdio process. It translates API requests into MCP tool calls and
manages the communication protocol.
"""

import json
import subprocess
import threading
import time
import uuid
import sys
import queue
from typing import Dict, Any, List, Optional
from flask import current_app
import os


class MCPClient:
    """Client for communicating with the MCP server via stdio protocol."""
    
    def __init__(self, server_command: str = None):
        """Initialize MCP client.
        
        Args:
            server_command: Command to run MCP server (defaults to environment variable or auto-detection)
        """
        self.server_command = server_command or self._get_mcp_server_command()
        if not self.server_command:
            raise ValueError("Unable to determine MCP server command. Please set MCP_SERVER_COMMAND environment variable.")
        
        self.process = None
        self.tools = {}
        self.is_connected = False
        self._lock = threading.Lock()
    
    def _get_mcp_server_command(self) -> str:
        """Get MCP server command with auto-detection for different deployment environments."""
        # First, try explicit environment variable
        env_command = os.getenv('MCP_SERVER_COMMAND')
        if env_command:
            return env_command
        
        # Auto-detect based on deployment environment
        import sys
        import platform
        from pathlib import Path
        
        # Determine the Python executable and script path
        python_exe = sys.executable
        
        # Get the current working directory or app root
        app_root = Path.cwd()
        script_path = "src/mcp_server/mcp_server.py"
        
        # Check if we're in a specific deployment environment
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        
        if environment in ['production', 'staging']:
            # Production/staging deployment
            if platform.system() == 'Windows':
                # Azure App Service Windows
                return f"{python_exe} {script_path}"
            else:
                # Linux container (Docker, Azure Container Apps, etc.)
                return f"python {script_path}"
        
        elif os.getenv('WEBSITE_SITE_NAME'):
            # Azure App Service detection
            return f"python {script_path}"
        
        elif os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER'):
            # Docker container detection
            return f"python {script_path}"
        
        elif platform.system() == 'Windows':
            # Local Windows development
            # Try to find venv python
            possible_python_paths = [
                app_root / '.venv' / 'Scripts' / 'python.exe',
                app_root / 'venv' / 'Scripts' / 'python.exe',
                python_exe
            ]
            
            for py_path in possible_python_paths:
                if Path(py_path).exists():
                    return f"{py_path} {script_path}"
            
            # Fallback to system python
            return f"python {script_path}"
        
        else:
            # Unix-like systems (Linux, macOS)
            # Try to find venv python
            possible_python_paths = [
                app_root / '.venv' / 'bin' / 'python',
                app_root / 'venv' / 'bin' / 'python',
                python_exe
            ]
            
            for py_path in possible_python_paths:
                if Path(py_path).exists():
                    return f"{py_path} {script_path}"
            
            # Fallback to system python
            return f"python {script_path}"
        
    def connect(self):
        """Start the MCP server process and establish connection."""
        try:
            current_app.logger.info(f"Starting MCP server with command: {self.server_command}")
            
            # Prepare environment variables for the MCP server
            mcp_env = os.environ.copy()
            
            # Add MCP-specific environment variables if they exist
            mcp_env_vars = [
                'MCP_SERVER_NAME',
                'LOG_LEVEL', 
                'API_TIMEOUT',
                'ENVIRONMENT',
                'VECTOR_SEARCH_API_URL'  # Pass the Vector API URL to MCP server
            ]
            
            for var in mcp_env_vars:
                if var in os.environ:
                    mcp_env[var] = os.environ[var]
                    current_app.logger.info(f"Passing environment variable to MCP server: {var}={os.environ[var]}")
            
            # Start the MCP server process
            self.process = subprocess.Popen(
                self.server_command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=mcp_env  # Pass the environment variables
            )
            
            # Give the process a moment to start
            import time
            time.sleep(0.5)
            
            # Check if process started successfully
            if self.process.poll() is not None:
                # Process has already terminated
                stderr_output = self.process.stderr.read()
                raise Exception(f"MCP server process failed to start. Exit code: {self.process.poll()}. Error: {stderr_output}")
            
            # Initialize the connection
            self._send_initialize()
            self._discover_tools()
            
            self.is_connected = True
            current_app.logger.info(f"MCP server connected successfully. Available tools: {len(self.tools)}")
            
        except Exception as e:
            current_app.logger.error(f"Failed to connect to MCP server: {str(e)}")
            self.disconnect()
            raise
    
    def disconnect(self):
        """Close the MCP server connection."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                current_app.logger.error(f"Error disconnecting MCP server: {str(e)}")
            finally:
                self.process = None
        
        self.is_connected = False
        current_app.logger.info("MCP server disconnected")
    
    def _send_initialize(self):
        """Send initialization request to MCP server."""
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "EPIC Search API",
                    "version": "1.0.0"
                }
            }
        }
        
        response = self._send_request(init_request)
        if response.get("error"):
            raise Exception(f"MCP initialization failed: {response['error']}")
        
        current_app.logger.info("MCP server initialized successfully")
    
    def _discover_tools(self):
        """Discover available tools from the MCP server."""
        tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        
        response = self._send_request(tools_request)
        if response.get("error"):
            raise Exception(f"Failed to discover MCP tools: {response['error']}")
        
        # Store available tools
        tools_list = response.get("result", {}).get("tools", [])
        for tool in tools_list:
            self.tools[tool["name"]] = tool
        
        current_app.logger.info(f"Discovered {len(self.tools)} MCP tools: {list(self.tools.keys())}")
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server and return the response."""
        if not self.process or self.process.poll() is not None:
            exit_code = self.process.poll() if self.process else "unknown"
            raise Exception(f"MCP server is not running (exit code: {exit_code})")
        
        with self._lock:
            try:
                # Send request
                request_json = json.dumps(request) + "\n"
                current_app.logger.debug(f"Sending MCP request: {request_json.strip()}")
                
                self.process.stdin.write(request_json)
                self.process.stdin.flush()
                
                # Read response with timeout
                import select
                import sys
                
                # Wait for response (with timeout)
                timeout = 30  # 30 second timeout
                if sys.platform == "win32":
                    # Windows doesn't support select on pipes, use threading for timeout
                    import threading
                    import queue
                    
                    def read_line(q):
                        try:
                            line = self.process.stdout.readline()
                            q.put(('data', line))
                        except Exception as e:
                            q.put(('error', str(e)))
                    
                    q = queue.Queue()
                    t = threading.Thread(target=read_line, args=(q,))
                    t.daemon = True
                    t.start()
                    
                    try:
                        result_type, response_line = q.get(timeout=timeout)
                        if result_type == 'error':
                            raise Exception(f"Error reading from MCP server: {response_line}")
                    except queue.Empty:
                        raise Exception(f"MCP server did not respond within {timeout} seconds")
                else:
                    # Unix systems can use select
                    ready, _, _ = select.select([self.process.stdout], [], [], timeout)
                    if not ready:
                        raise Exception(f"MCP server did not respond within {timeout} seconds")
                    response_line = self.process.stdout.readline()
                
                if not response_line:
                    # Check if process is still alive
                    if self.process.poll() is not None:
                        stderr_output = self.process.stderr.read()
                        raise Exception(f"MCP server process terminated. Exit code: {self.process.poll()}. Error: {stderr_output}")
                    raise Exception("No response from MCP server")
                
                response = json.loads(response_line.strip())
                current_app.logger.debug(f"Received MCP response: {response}")
                
                return response
                
            except json.JSONDecodeError as e:
                current_app.logger.error(f"Invalid JSON response from MCP server: {response_line}")
                raise Exception(f"Invalid JSON from MCP server: {str(e)}")
            except Exception as e:
                current_app.logger.error(f"Error in MCP communication: {str(e)}")
                raise
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a specific tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        if not self.is_connected:
            raise Exception("MCP client is not connected")
        
        if tool_name not in self.tools:
            raise Exception(f"Tool '{tool_name}' is not available. Available tools: {list(self.tools.keys())}")
        
        call_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {}
            }
        }
        
        current_app.logger.info(f"Calling MCP tool '{tool_name}' with arguments: {arguments}")
        response = self._send_request(call_request)
        
        if response.get("error"):
            current_app.logger.error(f"MCP tool call failed: {response['error']}")
            raise Exception(f"Tool call failed: {response['error']}")
        
        result = response.get("result", {})
        current_app.logger.info(f"MCP tool '{tool_name}' completed successfully")
        
        return result
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool."""
        return self.tools.get(tool_name)


# Global MCP client instance
_mcp_client = None


def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance."""
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MCPClient()
        try:
            _mcp_client.connect()
        except Exception as e:
            current_app.logger.error(f"Failed to initialize MCP client: {str(e)}")
            _mcp_client = None
            raise
    
    return _mcp_client


def ensure_mcp_connection():
    """Ensure MCP connection is active, reconnect if necessary."""
    global _mcp_client
    
    try:
        if _mcp_client is None or not _mcp_client.is_connected:
            current_app.logger.info("Re-establishing MCP connection...")
            _mcp_client = MCPClient()
            _mcp_client.connect()
    except Exception as e:
        current_app.logger.error(f"Failed to ensure MCP connection: {str(e)}")
        # Don't raise here - let individual methods handle fallbacks
        _mcp_client = None


def get_mcp_client_safe() -> Optional[MCPClient]:
    """Get MCP client with safe error handling and auto-recovery."""
    global _mcp_client
    
    try:
        # First, check if we have a client and if it's still healthy
        if _mcp_client is not None:
            # Check if the process is still alive
            if _mcp_client.process and _mcp_client.process.poll() is not None:
                current_app.logger.warning(f"MCP server process died (exit code: {_mcp_client.process.poll()}), reconnecting...")
                _mcp_client.disconnect()
                _mcp_client = None
            elif _mcp_client.is_connected:
                return _mcp_client
        
        # If we don't have a client or it's unhealthy, create a new one
        return get_mcp_client()
        
    except Exception as e:
        current_app.logger.warning(f"MCP client unavailable: {str(e)}")
        # Clean up broken client
        if _mcp_client:
            try:
                _mcp_client.disconnect()
            except:
                pass
            _mcp_client = None
        return None


def cleanup_mcp_client():
    """Clean up the MCP client connection."""
    global _mcp_client
    
    if _mcp_client:
        _mcp_client.disconnect()
        _mcp_client = None


def force_restart_mcp_client():
    """Force restart the MCP client - useful when it gets stuck."""
    global _mcp_client
    
    current_app.logger.info("Force restarting MCP client...")
    
    if _mcp_client:
        try:
            # Try graceful shutdown first
            _mcp_client.disconnect()
        except:
            # If graceful shutdown fails, kill the process
            if _mcp_client.process:
                try:
                    _mcp_client.process.kill()
                except:
                    pass
        _mcp_client = None
    
    # Create new client
    try:
        _mcp_client = MCPClient()
        _mcp_client.connect()
        current_app.logger.info("MCP client restarted successfully")
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to restart MCP client: {str(e)}")
        _mcp_client = None
        return False


def call_mcp_tool_with_retry(tool_name: str, arguments: Dict[str, Any] = None, max_retries: int = 2):
    """Call MCP tool with automatic retry and recovery on timeout/failure."""
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            client = get_mcp_client_safe()
            if not client:
                raise Exception("MCP client unavailable")
            
            # Try the tool call
            return client.call_tool(tool_name, arguments)
            
        except Exception as e:
            last_exception = e
            current_app.logger.warning(f"MCP tool call attempt {attempt + 1} failed: {str(e)}")
            
            if attempt < max_retries:
                current_app.logger.info(f"Retrying MCP tool call (attempt {attempt + 2}/{max_retries + 1})")
                # Force restart the client for the next attempt
                force_restart_mcp_client()
                time.sleep(1)  # Brief delay before retry
            else:
                current_app.logger.error(f"All MCP tool call attempts failed for '{tool_name}'")
    
    # If we get here, all attempts failed
    raise last_exception
