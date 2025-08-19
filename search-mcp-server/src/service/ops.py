"""
Operational endpoints for the MCP server.
Provides health, readiness, and liveness checks.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

app = FastAPI(title="EPIC Search MCP Server - Operations", version="1.0.0")


async def check_vector_api_connectivity() -> Dict[str, Any]:
    """Check if Vector API is reachable."""
    vector_api_url = os.getenv("VECTOR_SEARCH_API_URL")
    if not vector_api_url:
        return {
            "status": "fail",
            "message": "VECTOR_SEARCH_API_URL not configured"
        }
    
    try:
        # Try to reach the health endpoint or base URL
        health_url = f"{vector_api_url.rstrip('/')}/health"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(health_url)
            if response.status_code == 200:
                return {
                    "status": "pass",
                    "message": "Vector API connectivity confirmed",
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
                }
            else:
                return {
                    "status": "warn",
                    "message": f"Vector API responded with status {response.status_code}",
                    "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
                }
    except Exception as e:
        return {
            "status": "fail",
            "message": f"Vector API connectivity failed: {str(e)}"
        }


async def check_mcp_modules() -> Dict[str, Any]:
    """Check if MCP server modules can be imported."""
    try:
        from mcp_server.server import EPICSearchMCPServer
        from mcp_server.tools import search_tools, stats_tools
        return {
            "status": "pass",
            "message": "MCP server modules loaded successfully"
        }
    except ImportError as e:
        return {
            "status": "fail",
            "message": f"MCP module import failed: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "fail",
            "message": f"MCP module check failed: {str(e)}"
        }


async def check_environment() -> Dict[str, Any]:
    """Check environment configuration."""
    required_vars = ["VECTOR_SEARCH_API_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        return {
            "status": "fail",
            "message": f"Missing required environment variables: {', '.join(missing_vars)}"
        }
    
    return {
        "status": "pass",
        "message": "Environment configuration valid",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "log_level": os.getenv("LOG_LEVEL", "INFO")
    }


@app.get("/healthz")
async def healthz():
    """
    Health check endpoint - indicates if the service is alive.
    Returns 200 if the basic service is running.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "epic-search-mcp-server",
            "version": "1.0.0"
        }
    )


@app.get("/readyz")
async def readyz():
    """
    Readiness check endpoint - indicates if the service is ready to serve traffic.
    Performs comprehensive checks of dependencies and configuration.
    """
    checks = {}
    overall_status = "ready"
    
    # Check environment configuration
    env_check = await check_environment()
    checks["environment"] = env_check
    if env_check["status"] != "pass":
        overall_status = "not_ready"
    
    # Check MCP modules
    mcp_check = await check_mcp_modules()
    checks["mcp_modules"] = mcp_check
    if mcp_check["status"] != "pass":
        overall_status = "not_ready"
    
    # Check Vector API connectivity
    api_check = await check_vector_api_connectivity()
    checks["vector_api"] = api_check
    if api_check["status"] == "fail":
        overall_status = "not_ready"
    elif api_check["status"] == "warn" and overall_status == "ready":
        overall_status = "degraded"
    
    status_code = 200 if overall_status in ["ready", "degraded"] else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "epic-search-mcp-server",
            "checks": checks
        }
    )


@app.get("/livez")
async def livez():
    """
    Liveness check endpoint - indicates if the service should be restarted.
    Returns 200 if the service is alive and responding.
    """
    try:
        # Basic liveness check - can we import core modules?
        mcp_check = await check_mcp_modules()
        if mcp_check["status"] == "pass":
            return JSONResponse(
                status_code=200,
                content={
                    "status": "alive",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": "epic-search-mcp-server"
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": "epic-search-mcp-server",
                    "error": mcp_check["message"]
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "epic-search-mcp-server",
                "error": str(e)
            }
        )


@app.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint for monitoring.
    """
    try:
        # Basic service metrics
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat(),
                "service": "epic-search-mcp-server",
                "uptime": "available",  # Could be enhanced with actual uptime tracking
                "environment": os.getenv("ENVIRONMENT", "development"),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
                "vector_api_configured": bool(os.getenv("VECTOR_SEARCH_API_URL"))
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "metrics_error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
