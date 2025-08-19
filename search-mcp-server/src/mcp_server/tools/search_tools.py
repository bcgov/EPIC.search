"""Search tools for MCP server.

These tools expose the vector search API's search capabilities to LLM agents,
including vector search, similarity search, and document retrieval.
"""

import json
from typing import Any, Dict, List
import httpx
import logging
from mcp.types import Tool

class SearchTools:
    """Handler for search-related MCP tools."""
    
    def __init__(self, http_client: httpx.AsyncClient, vector_api_base_url: str):
        """Initialize search tools with HTTP client and API base URL."""
        self.http_client = http_client
        self.vector_api_base_url = vector_api_base_url
        self.logger = logging.getLogger(__name__)
    
    def get_tools(self) -> List[Tool]:
        """Get list of available search tools."""
        return [
            Tool(
                name="vector_search",
                description="Perform vector similarity search through documents with advanced parameters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "The search query to find relevant documents"
                        },
                        "project_ids": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "Optional list of project IDs to filter by"
                        },
                        "document_type_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of document type IDs to filter by"
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
            ),
            
            Tool(
                name="find_similar_documents",
                description="Find documents similar to a specific document using vector similarity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "ID of the document to find similarities for"
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of project IDs to filter by"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "maximum": 50,
                            "description": "Maximum number of similar documents to return"
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            
            Tool(
                name="search_with_auto_inference",
                description="Smart search that automatically determines best projects and document types based on query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query - the system will intelligently determine relevant projects and document types"
                        },
                        "confidence_threshold": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.5,
                            "description": "Confidence threshold for automatic filtering"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "maximum": 50,
                            "description": "Maximum number of results to return"
                        }
                    },
                    "required": ["query"]
                }
            ),
            
            Tool(
                name="get_available_projects",
                description="Get list of available projects for filtering search results",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters needed - returns all available projects"
                }
            ),
            
            Tool(
                name="get_available_document_types",
                description="Get list of available document types for filtering search results",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters needed - returns all document types with metadata and aliases"
                }
            ),
            
            Tool(
                name="get_document_type_details",
                description="Get detailed information about a specific document type",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_type_id": {
                            "type": "string",
                            "description": "The document type ID to get details for"
                        }
                    },
                    "required": ["document_type_id"]
                }
            ),
            
            Tool(
                name="suggest_filters",
                description="Analyze a query and suggest optimal project and document type filters",
                inputSchema={
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
            ),
            
            Tool(
                name="get_search_strategies",
                description="Get all available search strategies (semantic, keyword, hybrid, metadata) with their capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            
            Tool(
                name="get_inference_options",
                description="Get available ML inference services (document type, project classification) with capabilities",
                inputSchema={
                    "type": "object", 
                    "properties": {}
                }
            ),
            
            Tool(
                name="get_api_capabilities",
                description="Complete API metadata and endpoint discovery for dynamic client generation",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            
            Tool(
                name="document_similarity_search",
                description="Find documents similar to a specific document using document-level embeddings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The document ID to find similar documents for"
                        },
                        "project_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of project IDs to filter similar documents by"
                        },
                        "limit": {
                            "type": "integer",
                            "default": 10,
                            "maximum": 50,
                            "description": "Maximum number of similar documents to return"
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            
            Tool(
                name="agentic_search",
                description="Intelligent search designed for agentic mode - combines multiple search strategies and provides comprehensive results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query from the user"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about what the user is looking for"
                        },
                        "user_intent": {
                            "type": "string",
                            "enum": ["find_documents", "find_similar", "explore_topic", "get_overview", "specific_lookup"],
                            "description": "The detected user intent to guide search strategy"
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 15,
                            "maximum": 50,
                            "description": "Maximum number of results to return"
                        },
                        "include_stats": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to include processing statistics in the response"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls for search operations."""
        if name == "vector_search":
            return await self._vector_search(arguments)
        elif name == "find_similar_documents":
            return await self._find_similar_documents(arguments)
        elif name == "search_with_auto_inference":
            return await self._search_with_auto_inference(arguments)
        elif name == "get_available_projects":
            return await self._get_available_projects(arguments)
        elif name == "get_available_document_types":
            return await self._get_available_document_types(arguments)
        elif name == "get_document_type_details":
            return await self._get_document_type_details(arguments)
        elif name == "get_search_strategies":
            return await self._get_search_strategies(arguments)
        elif name == "get_inference_options":
            return await self._get_inference_options(arguments)
        elif name == "get_api_capabilities":
            return await self._get_api_capabilities(arguments)
        elif name == "document_similarity_search":
            return await self._document_similarity_search(arguments)
        elif name == "suggest_filters":
            return await self._suggest_filters(arguments)
        elif name == "agentic_search":
            return await self._agentic_search(arguments)
        else:
            raise ValueError(f"Unknown search tool: {name}")
    
    async def _vector_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute vector search with all available parameters."""
        try:
            # Prepare payload matching the vector search API format
            payload = {"query": args["query"]}
            
            # Add optional parameters if provided
            if "project_ids" in args and args["project_ids"]:
                payload["projectIds"] = args["project_ids"]
            if "document_type_ids" in args and args["document_type_ids"]:
                payload["documentTypeIds"] = args["document_type_ids"]
            if "inference" in args and args["inference"]:
                payload["inference"] = args["inference"]
            if "ranking" in args and args["ranking"]:
                payload["ranking"] = args["ranking"]
            if "search_strategy" in args and args["search_strategy"]:
                payload["searchStrategy"] = args["search_strategy"]
            
            self.logger.info(f"Calling vector search API with payload: {payload}")
            
            # Call the vector search API
            response = await self.http_client.post(
                f"{self.vector_api_base_url}/vector-search",
                json=payload
            )
            response.raise_for_status()
            
            api_response = response.json()
            
            # Extract relevant data and add tool metadata
            result = {
                "tool": "vector_search",
                "query": args["query"],
                "parameters_used": payload,
                "api_response": api_response
            }
            
            # Extract key information for easier LLM processing
            if "vector_search" in api_response:
                vector_data = api_response["vector_search"]
                result["summary"] = {
                    "documents_found": len(vector_data.get("documents", []) or vector_data.get("document_chunks", [])),
                    "search_quality": vector_data.get("search_quality", "unknown"),
                    "search_mode": vector_data.get("search_mode", "unknown"),
                    "original_query": vector_data.get("original_query", ""),
                    "semantic_query": vector_data.get("final_semantic_query", ""),
                    "project_inference": vector_data.get("project_inference", {}),
                    "document_type_inference": vector_data.get("document_type_inference", {})
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Vector search error: {str(e)}")
            return {
                "tool": "vector_search",
                "error": str(e),
                "query": args.get("query", ""),
                "parameters": args
            }
    
    async def _find_similar_documents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find documents similar to a specific document."""
        try:
            payload = {
                "documentId": args["document_id"],
                "limit": args.get("limit", 10)
            }
            
            if "project_ids" in args and args["project_ids"]:
                payload["projectIds"] = args["project_ids"]
            
            self.logger.info(f"Calling similarity search API with payload: {payload}")
            
            response = await self.http_client.post(
                f"{self.vector_api_base_url}/vector-search/similar",
                json=payload
            )
            response.raise_for_status()
            
            api_response = response.json()
            
            result = {
                "tool": "find_similar_documents",
                "source_document_id": args["document_id"],
                "parameters_used": payload,
                "api_response": api_response
            }
            
            # Extract summary information
            if "document_similarity" in api_response:
                similarity_data = api_response["document_similarity"]
                result["summary"] = {
                    "source_document_id": similarity_data.get("source_document_id", ""),
                    "similar_documents_found": len(similarity_data.get("documents", [])),
                    "search_metrics": similarity_data.get("search_metrics", {})
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Similar documents search error: {str(e)}")
            return {
                "tool": "find_similar_documents",
                "error": str(e),
                "document_id": args.get("document_id", ""),
                "parameters": args
            }
    
    async def _search_with_auto_inference(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform search with automatic project and document type inference."""
        try:
            # Use both PROJECT and DOCUMENTTYPE inference for smart filtering
            payload = {
                "query": args["query"],
                "inference": ["PROJECT", "DOCUMENTTYPE"],
                "ranking": {
                    "topN": args.get("max_results", 10)
                }
            }
            
            # Use hybrid search strategy for best results
            payload["searchStrategy"] = "HYBRID_SEMANTIC_FALLBACK"
            
            self.logger.info(f"Calling auto-inference search API with payload: {payload}")
            
            response = await self.http_client.post(
                f"{self.vector_api_base_url}/vector-search",
                json=payload
            )
            response.raise_for_status()
            
            api_response = response.json()
            
            result = {
                "tool": "search_with_auto_inference",
                "query": args["query"],
                "parameters_used": payload,
                "api_response": api_response
            }
            
            # Provide detailed summary of inference results
            if "vector_search" in api_response:
                vector_data = api_response["vector_search"]
                result["inference_analysis"] = {
                    "query_processed": vector_data.get("query_processed", False),
                    "semantic_cleaning_applied": vector_data.get("semantic_cleaning_applied", False),
                    "project_inference": vector_data.get("project_inference", {}),
                    "document_type_inference": vector_data.get("document_type_inference", {}),
                    "search_quality": vector_data.get("search_quality", "unknown"),
                    "documents_found": len(vector_data.get("documents", []) or vector_data.get("document_chunks", []))
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Auto-inference search error: {str(e)}")
            return {
                "tool": "search_with_auto_inference",
                "error": str(e),
                "query": args.get("query", ""),
                "parameters": args
            }

    async def _get_available_projects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of available projects using the Vector API tools endpoint."""
        try:
            self.logger.info("Fetching available projects from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/projects"
            )
            response.raise_for_status()
            
            projects_response = response.json()
            
            # Extract projects from the response structure: {"projects": [...]}
            projects = projects_response.get("projects", [])
            
            result = {
                "tool": "get_available_projects",
                "projects": projects,
                "total_projects": len(projects),
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            self.logger.info(f"Retrieved {result['total_projects']} projects")
            return result
            
        except Exception as e:
            self.logger.error(f"Get available projects error: {str(e)}")
            return {
                "tool": "get_available_projects",
                "error": str(e),
                "parameters": args
            }

    async def _get_available_document_types(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of available document types using the Vector API tools endpoint."""
        try:
            self.logger.info("Fetching available document types from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/document-types"
            )
            response.raise_for_status()
            
            doc_types_response = response.json()
            
            # Extract document_types from the response structure: {"document_types": {...}}
            doc_types_dict = doc_types_response.get("document_types", {})
            
            # Convert the dictionary format to a list for easier LLM consumption
            document_types = []
            for doc_type_id, doc_type_info in doc_types_dict.items():
                document_types.append({
                    "document_type_id": doc_type_id,
                    "name": doc_type_info.get("name", ""),
                    "aliases": doc_type_info.get("aliases", [])
                })
            
            result = {
                "tool": "get_available_document_types",
                "document_types": document_types,
                "raw_response": doc_types_dict,  # Keep original format for reference
                "total_document_types": len(document_types),
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            self.logger.info(f"Retrieved {result['total_document_types']} document types")
            return result
            
        except Exception as e:
            self.logger.error(f"Get available document types error: {str(e)}")
            return {
                "tool": "get_available_document_types",
                "error": str(e),
                "parameters": args
            }

    async def _get_document_type_details(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific document type."""
        try:
            document_type_id = args["document_type_id"]
            
            self.logger.info(f"Fetching details for document type: {document_type_id}")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/document-types/{document_type_id}"
            )
            response.raise_for_status()
            
            doc_type_response = response.json()
            
            # Extract document_type from the response structure: {"document_type": {...}}
            document_type = doc_type_response.get("document_type", {})
            
            result = {
                "tool": "get_document_type_details",
                "document_type_id": document_type_id,
                "document_type": {
                    "id": document_type.get("id", document_type_id),
                    "name": document_type.get("name", ""),
                    "aliases": document_type.get("aliases", [])
                },
                "raw_response": doc_type_response,  # Keep original format for reference
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Get document type details error: {str(e)}")
            return {
                "tool": "get_document_type_details",
                "error": str(e),
                "document_type_id": args.get("document_type_id", ""),
                "parameters": args
            }

    async def _suggest_filters(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query and suggest optimal filters using the inference pipeline."""
        try:
            query = args["query"]
            context = args.get("context", "")
            confidence_threshold = args.get("confidence_threshold", 0.6)
            
            # First, get available projects and document types
            projects_response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/projects"
            )
            doc_types_response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/document-types"
            )
            
            available_projects = projects_response.json() if projects_response.status_code == 200 else []
            available_doc_types = doc_types_response.json() if doc_types_response.status_code == 200 else []
            
            # Use the vector API's inference capabilities to suggest filters
            inference_payload = {
                "query": query,
                "inference": ["PROJECT", "DOCUMENTTYPE"],
                "ranking": {"topN": 1}  # We just want the inference, not actual results
            }
            
            self.logger.info(f"Getting filter suggestions for query: {query}")
            
            response = await self.http_client.post(
                f"{self.vector_api_base_url}/vector-search",
                json=inference_payload
            )
            response.raise_for_status()
            
            api_response = response.json()
            
            suggestions = {
                "tool": "suggest_filters",
                "query": query,
                "context": context,
                "confidence_threshold": confidence_threshold,
                "suggested_filters": {},
                "inference_data": {},
                "recommendations": [],
                "available_options": {
                    "total_projects": len(available_projects),
                    "total_document_types": len(available_doc_types)
                }
            }
            
            # Extract inference results
            if "vector_search" in api_response:
                vector_data = api_response["vector_search"]
                
                # Project inference
                if "project_inference" in vector_data:
                    project_inf = vector_data["project_inference"]
                    suggestions["inference_data"]["projects"] = project_inf
                    
                    # Filter by confidence threshold and match with available projects
                    high_conf_projects = []
                    for proj_id, confidence in project_inf.items():
                        if isinstance(confidence, (int, float)) and confidence >= confidence_threshold:
                            # Find project name from available projects
                            project_name = "Unknown"
                            for proj in available_projects:
                                if proj.get("project_id") == proj_id or proj.get("id") == proj_id:
                                    project_name = proj.get("project_name", proj.get("name", "Unknown"))
                                    break
                            
                            high_conf_projects.append({
                                "project_id": proj_id,
                                "project_name": project_name,
                                "confidence": confidence
                            })
                    
                    if high_conf_projects:
                        suggestions["suggested_filters"]["projectIds"] = [p["project_id"] for p in high_conf_projects]
                        suggestions["recommendations"].append(f"Recommended {len(high_conf_projects)} projects with confidence >= {confidence_threshold}")
                
                # Document type inference  
                if "document_type_inference" in vector_data:
                    doc_type_inf = vector_data["document_type_inference"]
                    suggestions["inference_data"]["document_types"] = doc_type_inf
                    
                    # Filter by confidence threshold and match with available document types
                    high_conf_doc_types = []
                    for doc_type_id, confidence in doc_type_inf.items():
                        if isinstance(confidence, (int, float)) and confidence >= confidence_threshold:
                            # Find document type name from available types
                            doc_type_name = "Unknown"
                            for doc_type in available_doc_types:
                                if doc_type.get("document_type_id") == doc_type_id or doc_type.get("id") == doc_type_id:
                                    doc_type_name = doc_type.get("name", "Unknown")
                                    break
                            
                            high_conf_doc_types.append({
                                "document_type_id": doc_type_id,
                                "document_type_name": doc_type_name,
                                "confidence": confidence
                            })
                    
                    if high_conf_doc_types:
                        suggestions["suggested_filters"]["documentTypeIds"] = [d["document_type_id"] for d in high_conf_doc_types]
                        suggestions["recommendations"].append(f"Recommended {len(high_conf_doc_types)} document types with confidence >= {confidence_threshold}")
            
            # Add fallback recommendations
            if not suggestions["suggested_filters"]:
                suggestions["recommendations"].append("No high-confidence filters found. Consider using inference mode or searching all projects/document types.")
                suggestions["recommendations"].append("You can call get_available_projects and get_available_document_types to see all options.")
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Suggest filters error: {str(e)}")
            return {
                "tool": "suggest_filters",
                "error": str(e),
                "query": args.get("query", ""),
                "parameters": args
            }

    async def _agentic_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Perform intelligent agentic search with multiple strategies and comprehensive results."""
        try:
            query = args["query"]
            user_intent = args.get("user_intent", "find_documents")
            max_results = args.get("max_results", 15)
            include_stats = args.get("include_stats", False)
            context = args.get("context", "")
            
            # Build search strategy based on user intent
            search_strategies = []
            
            if user_intent in ["find_documents", "explore_topic", "get_overview"]:
                # Use hybrid search with inference for comprehensive results
                search_strategies.append({
                    "name": "hybrid_with_inference",
                    "payload": {
                        "query": query,
                        "inference": ["PROJECT", "DOCUMENTTYPE"],
                        "searchStrategy": "HYBRID_SEMANTIC_FALLBACK",
                        "ranking": {"topN": max_results}
                    }
                })
            
            if user_intent in ["specific_lookup", "find_similar"]:
                # Use semantic search for more precise results
                search_strategies.append({
                    "name": "semantic_focused",
                    "payload": {
                        "query": query,
                        "searchStrategy": "SEMANTIC_ONLY",
                        "ranking": {"topN": max_results, "minScore": 0.7}
                    }
                })
            
            # Default to hybrid search if no specific strategy
            if not search_strategies:
                search_strategies.append({
                    "name": "default_hybrid",
                    "payload": {
                        "query": query,
                        "searchStrategy": "HYBRID_SEMANTIC_FALLBACK",
                        "ranking": {"topN": max_results}
                    }
                })
            
            # Execute search strategies
            results = {}
            total_documents = 0
            
            for strategy in search_strategies:
                try:
                    self.logger.info(f"Executing agentic search strategy: {strategy['name']}")
                    
                    response = await self.http_client.post(
                        f"{self.vector_api_base_url}/vector-search",
                        json=strategy["payload"]
                    )
                    response.raise_for_status()
                    
                    strategy_result = response.json()
                    results[strategy["name"]] = strategy_result
                    
                    # Count documents from this strategy
                    if "vector_search" in strategy_result:
                        docs = strategy_result["vector_search"].get("documents", []) or strategy_result["vector_search"].get("document_chunks", [])
                        total_documents += len(docs)
                        
                except Exception as e:
                    self.logger.error(f"Strategy {strategy['name']} failed: {str(e)}")
                    results[strategy["name"]] = {"error": str(e)}
            
            # Prepare comprehensive result
            agentic_result = {
                "tool": "agentic_search",
                "query": query,
                "user_intent": user_intent,
                "context": context,
                "strategies_executed": len(search_strategies),
                "total_documents_found": total_documents,
                "search_results": results,
                "metadata": {
                    "max_results_requested": max_results,
                    "include_stats": include_stats,
                    "timestamp": "2025-08-18T00:00:00Z"  # You might want to use actual timestamp
                }
            }
            
            # Add processing stats if requested
            if include_stats:
                try:
                    stats_response = await self.http_client.get(
                        f"{self.vector_api_base_url}/stats/processing"
                    )
                    if stats_response.status_code == 200:
                        agentic_result["system_stats"] = stats_response.json()
                except Exception as e:
                    self.logger.warning(f"Could not fetch stats: {str(e)}")
            
            # Extract summary for easier LLM consumption
            agentic_result["summary"] = self._create_agentic_summary(results, query, user_intent)
            
            return agentic_result
            
        except Exception as e:
            self.logger.error(f"Agentic search error: {str(e)}")
            return {
                "tool": "agentic_search",
                "error": str(e),
                "query": args.get("query", ""),
                "parameters": args
            }
    
    def _create_agentic_summary(self, results: Dict, query: str, user_intent: str) -> Dict[str, Any]:
        """Create a summary of agentic search results for easier LLM consumption."""
        summary = {
            "query": query,
            "intent": user_intent,
            "successful_strategies": 0,
            "total_unique_documents": 0,
            "best_strategy": None,
            "quality_indicators": {}
        }
        
        best_doc_count = 0
        
        for strategy_name, result in results.items():
            if "error" not in result and "vector_search" in result:
                summary["successful_strategies"] += 1
                
                vector_data = result["vector_search"]
                docs = vector_data.get("documents", []) or vector_data.get("document_chunks", [])
                doc_count = len(docs)
                
                if doc_count > best_doc_count:
                    best_doc_count = doc_count
                    summary["best_strategy"] = strategy_name
                
                # Extract quality indicators
                summary["quality_indicators"][strategy_name] = {
                    "document_count": doc_count,
                    "search_quality": vector_data.get("search_quality", "unknown"),
                    "search_mode": vector_data.get("search_mode", "unknown")
                }
        
        summary["total_unique_documents"] = best_doc_count  # Simplified - you might want to deduplicate
        
        return summary

    async def _get_search_strategies(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get all available search strategies with their capabilities."""
        try:
            self.logger.info("Fetching available search strategies from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/search-strategies"
            )
            response.raise_for_status()
            
            strategies_data = response.json()
            
            result = {
                "tool": "get_search_strategies",
                "search_strategies": strategies_data,
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Get search strategies error: {str(e)}")
            return {
                "tool": "get_search_strategies",
                "error": str(e),
                "parameters": args
            }

    async def _get_inference_options(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get available ML inference services with their capabilities."""
        try:
            self.logger.info("Fetching available inference options from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/inference-options"
            )
            response.raise_for_status()
            
            inference_data = response.json()
            
            result = {
                "tool": "get_inference_options",
                "inference_options": inference_data,
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Get inference options error: {str(e)}")
            return {
                "tool": "get_inference_options",
                "error": str(e),
                "parameters": args
            }

    async def _get_api_capabilities(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get complete API metadata and endpoint discovery."""
        try:
            self.logger.info("Fetching API capabilities from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/api-capabilities"
            )
            response.raise_for_status()
            
            capabilities_data = response.json()
            
            result = {
                "tool": "get_api_capabilities",
                "api_capabilities": capabilities_data,
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Get API capabilities error: {str(e)}")
            return {
                "tool": "get_api_capabilities",
                "error": str(e),
                "parameters": args
            }

    async def _document_similarity_search(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Find documents similar to a specific document using document-level embeddings."""
        try:
            document_id = args["document_id"]
            project_ids = args.get("project_ids", [])
            limit = args.get("limit", 10)
            
            payload = {
                "document_id": document_id,
                "limit": limit
            }
            
            if project_ids:
                payload["project_ids"] = project_ids
            
            self.logger.info(f"Finding similar documents for: {document_id}")
            
            response = await self.http_client.post(
                f"{self.vector_api_base_url}/document-similarity",
                json=payload
            )
            response.raise_for_status()
            
            similarity_data = response.json()
            
            result = {
                "tool": "document_similarity_search",
                "document_id": document_id,
                "similar_documents": similarity_data,
                "metadata": {
                    "source": "vector_api_similarity_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            # Extract summary information
            if "similar_documents" in similarity_data:
                result["summary"] = {
                    "source_document_id": document_id,
                    "similar_documents_found": len(similarity_data["similar_documents"]),
                    "project_filter_applied": bool(project_ids),
                    "limit_requested": limit
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Document similarity search error: {str(e)}")
            return {
                "tool": "document_similarity_search",
                "error": str(e),
                "document_id": args.get("document_id", ""),
                "parameters": args
            }
