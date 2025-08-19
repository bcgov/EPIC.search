"""Stats tools for MCP server.

These tools expose the vector search API's statistics and monitoring capabilities
to LLM agents for understanding system performance and processing status.
"""

import json
from typing import Any, Dict, List
import httpx
import logging
from mcp.types import Tool

class StatsTools:
    """Handler for statistics-related MCP tools."""
    
    def __init__(self, http_client: httpx.AsyncClient, vector_api_base_url: str):
        """Initialize stats tools with HTTP client and API base URL."""
        self.http_client = http_client
        self.vector_api_base_url = vector_api_base_url
        self.logger = logging.getLogger(__name__)
    
    def get_tools(self) -> List[Tool]:
        """Get list of available statistics tools."""
        return [
            Tool(
                name="get_processing_stats",
                description="Get processing statistics for projects including successful, failed, and skipped file counts",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Optional project ID to filter stats. If not provided, returns stats for all projects"
                        }
                    }
                }
            ),
            
            Tool(
                name="get_project_details",
                description="Get detailed processing logs and information for a specific project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The project ID to get detailed information for"
                        }
                    },
                    "required": ["project_id"]
                }
            ),
            
            Tool(
                name="get_system_summary",
                description="Get high-level processing summary across the entire system",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls for statistics operations."""
        if name == "get_processing_stats":
            return await self._get_processing_stats(arguments)
        elif name == "get_project_details":
            return await self._get_project_details(arguments)
        elif name == "get_system_summary":
            return await self._get_system_summary(arguments)
        else:
            raise ValueError(f"Unknown stats tool: {name}")
    
    async def _get_processing_stats(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get processing statistics from the vector API."""
        try:
            project_id = args.get("project_id")
            
            # Always use GET with query parameters
            params = {}
            if project_id:
                params["project_id"] = project_id
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/stats/processing",
                params=params
            )
            
            response.raise_for_status()
            api_response = response.json()
            
            result = {
                "tool": "get_processing_stats",
                "filtered_by_project": project_id is not None,
                "project_filter": project_id,
                "api_response": api_response
            }
            
            # Add summary analysis
            if "processing_stats" in api_response:
                stats = api_response["processing_stats"]
                projects = stats.get("projects", [])
                summary = stats.get("summary", {})
                
                result["analysis"] = {
                    "total_projects": len(projects),
                    "overall_stats": summary,
                    "project_breakdown": [
                        {
                            "project_id": p.get("project_id"),
                            "project_name": p.get("project_name"),
                            "success_rate": p.get("success_rate", 0),
                            "total_files": p.get("total_files", 0),
                            "file_status": {
                                "successful": p.get("successful_files", 0),
                                "failed": p.get("failed_files", 0),
                                "skipped": p.get("skipped_files", 0)
                            }
                        }
                        for p in projects
                    ]
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Processing stats error: {str(e)}")
            return {
                "tool": "get_processing_stats",
                "error": str(e),
                "parameters": args
            }
    
    async def _get_project_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information for a specific project."""
        try:
            project_id = args["project_id"]
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/stats/project/{project_id}"
            )
            response.raise_for_status()
            
            api_response = response.json()
            
            result = {
                "tool": "get_project_details",
                "project_id": project_id,
                "api_response": api_response
            }
            
            # Add analysis of project details
            if "project_details" in api_response:
                details = api_response["project_details"]
                processing_logs = details.get("processing_logs", [])
                summary = details.get("summary", {})
                
                # Analyze processing patterns
                status_counts = {}
                for log in processing_logs:
                    status = log.get("status", "unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                result["analysis"] = {
                    "project_summary": summary,
                    "processing_log_count": len(processing_logs),
                    "status_breakdown": status_counts,
                    "recent_processing": processing_logs[-10:] if processing_logs else []  # Last 10 entries
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Project details error: {str(e)}")
            return {
                "tool": "get_project_details",
                "error": str(e),
                "project_id": args.get("project_id", ""),
                "parameters": args
            }
    
    async def _get_system_summary(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get system-wide processing summary."""
        try:
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/stats/summary"
            )
            response.raise_for_status()
            
            api_response = response.json()
            
            result = {
                "tool": "get_system_summary",
                "api_response": api_response
            }
            
            # Add high-level system analysis
            if "summary" in api_response:
                summary = api_response["summary"]
                
                result["system_health"] = {
                    "total_projects": summary.get("total_projects", 0),
                    "total_documents": summary.get("total_documents", 0),
                    "overall_success_rate": summary.get("overall_success_rate", 0),
                    "projects_with_failures": summary.get("projects_with_failures", 0),
                    "system_status": "healthy" if summary.get("overall_success_rate", 0) > 90 else "needs_attention"
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"System summary error: {str(e)}")
            return {
                "tool": "get_system_summary",
                "error": str(e),
                "parameters": args
            }
    
