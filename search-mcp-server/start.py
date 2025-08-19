#!/bin/bash
"""
Startup script for EPIC Search MCP Server.
Starts both the MCP server and the operational endpoints.
"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def start_ops_server():
    """Start the operations server with health endpoints."""
    return subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "service.ops:app",
        "--host", "0.0.0.0",
        "--port", "8001",
        "--log-level", "info"
    ], cwd=str(Path(__file__).parent))

def start_mcp_server():
    """Start the main MCP server."""
    return subprocess.Popen([
        sys.executable, "main.py"
    ], cwd=str(Path(__file__).parent))

def main():
    """Start both servers and handle graceful shutdown."""
    print("🚀 Starting EPIC Search MCP Server...")
    
    # Start the operations server
    print("📊 Starting operations server on port 8001...")
    ops_process = start_ops_server()
    
    # Start the MCP server
    print("🔧 Starting MCP server on port 8000...")
    mcp_process = start_mcp_server()
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down...")
        ops_process.terminate()
        mcp_process.terminate()
        ops_process.wait()
        mcp_process.wait()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("✅ Both servers started successfully!")
    print("📊 Health endpoints: http://localhost:8001/healthz, /readyz, /livez")
    print("🔧 MCP server: http://localhost:8000")
    print("Press Ctrl+C to stop...")
    
    try:
        # Wait for both processes
        while True:
            if ops_process.poll() is not None:
                print("❌ Operations server exited")
                break
            if mcp_process.poll() is not None:
                print("❌ MCP server exited")
                break
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 Stopping servers...")
        ops_process.terminate()
        mcp_process.terminate()
        ops_process.wait()
        mcp_process.wait()

if __name__ == "__main__":
    main()
