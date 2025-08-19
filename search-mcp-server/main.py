#!/usr/bin/env python3
"""Main entry point for EPIC Search MCP Server."""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
