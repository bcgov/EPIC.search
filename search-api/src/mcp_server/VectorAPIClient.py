"""
Vector API Client Interface for Your API
========================================

This is the interface your API should implement to work with the MCP server.

Implementation Guide:
1. Your API implements this VectorAPIClient class
2. LLM uses MCP tools to get recommendations  
3. LLM returns instructions to your API
4. Your API executes using this client
5. Your API returns results to website

Tool Categories:
- Direct API Methods (13): Map directly to your Vector API endpoints
- Intelligent Methods (2): Your API implements using LLM + multiple Vector API calls
"""

from typing import List, Dict, Any, Optional
import httpx


class VectorAPIClient:
    """
    Vector API client that your API should implement.
    The MCP server returns recommendations for these method calls.
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    # =============================================================================
    # DIRECT API SEARCH OPERATIONS - These map directly to your Vector API
    # =============================================================================
    
    async def vector_search(
        self,
        query: str,
        project_ids: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        inference: bool = False,
        search_strategy: Optional[str] = None,
        max_results: int = 50,
        similarity_threshold: float = 0.7,
        ranking_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Two-stage hybrid search with advanced parameters.
        MCP tool 'vector_search' provides optimized parameters for this call.
        """
        payload = {
            "query": query,
            "max_results": max_results,
            "similarity_threshold": similarity_threshold
        }
        
        if project_ids:
            payload["project_ids"] = project_ids
        if document_types:
            payload["document_types"] = document_types
        if inference:
            payload["inference"] = inference
        if search_strategy:
            payload["search_strategy"] = search_strategy
        if ranking_strategy:
            payload["ranking_strategy"] = ranking_strategy
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/vector-search",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def find_similar_documents(
        self,
        document_id: str,
        max_results: int = 10,
        similarity_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Find documents similar to a specific document (legacy endpoint).
        MCP tool 'find_similar_documents' provides parameters.
        """
        payload = {
            "documentId": document_id,
            "limit": max_results,
            "similarity_threshold": similarity_threshold
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/document-similarity",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def document_similarity_search(
        self,
        document_id: str,
        max_results: int = 10,
        similarity_threshold: float = 0.8,
        project_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Document-level embedding similarity search.
        MCP tool 'document_similarity_search' provides parameters.
        """
        payload = {
            "documentId": document_id,
            "limit": max_results,
            "similarity_threshold": similarity_threshold
        }
        
        if project_ids:
            payload["projectIds"] = project_ids
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/document-similarity",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def search_with_auto_inference(
        self,
        query: str,
        context: Optional[str] = None,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Smart search with automatic project and document type inference.
        
        IMPLEMENTATION NOTE: Your Vector API doesn't have an /inference-search endpoint.
        Your API client should implement this by:
        1. Using LLM with MCP tools to analyze the query
        2. Calling get_available_projects() and get_available_document_types()
        3. Making an enhanced vector_search() call with inferred parameters
        
        This method is a placeholder - replace with your implementation logic.
        """
        # Your API client implements this using LLM analysis + vector_search()
        # This is NOT a direct Vector API call
        raise NotImplementedError(
            "Your API client must implement this using LLM analysis + vector_search(). "
            "This is not a direct Vector API endpoint."
        )
    
    # =============================================================================
    # DISCOVERY OPERATIONS - These map directly to your Vector API /api/tools/ endpoints
    # =============================================================================
    
    async def get_available_projects(self) -> Dict[str, Any]:
        """
        Retrieve all available projects with metadata.
        MCP tool 'get_available_projects' calls this to help LLM understand filtering options.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tools/projects",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_available_document_types(self) -> Dict[str, Any]:
        """
        Get document types with aliases and descriptions.
        MCP tool 'get_available_document_types' calls this for intelligent filtering.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tools/document-types",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_document_type_details(self, document_type: str) -> Dict[str, Any]:
        """
        Get detailed information for a specific document type.
        MCP tool 'get_document_type_details' calls this for context.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tools/document-types/{document_type}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_search_strategies(self) -> Dict[str, Any]:
        """
        Retrieve available search strategies and capabilities.
        MCP tool 'get_search_strategies' calls this for strategy selection.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tools/search-strategies",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_inference_options(self) -> Dict[str, Any]:
        """
        Get available ML inference services and options.
        MCP tool 'get_inference_options' calls this for capability discovery.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tools/inference-options",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_api_capabilities(self) -> Dict[str, Any]:
        """
        Complete API metadata discovery for adaptive clients.
        MCP tool 'get_api_capabilities' calls this for comprehensive API understanding.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/tools/api-capabilities",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    # =============================================================================
    # INTELLIGENT OPERATIONS - Your API client implements these, NOT your Vector API
    # =============================================================================
    
    async def suggest_filters(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        AI-powered filter recommendations based on query analysis.
        
        IMPLEMENTATION NOTE: Your Vector API doesn't have a /suggest-filters endpoint.
        Your API client should implement this by:
        1. Using LLM with MCP tools to analyze the query
        2. Calling get_available_projects() and get_available_document_types()
        3. Using AI to recommend optimal project_ids and document_types
        
        This method is a placeholder - replace with your implementation logic.
        """
        # Your API client implements this using LLM analysis + discovery tools
        # This is NOT a direct Vector API call
        raise NotImplementedError(
            "Your API client must implement this using LLM analysis + discovery tools. "
            "This is not a direct Vector API endpoint."
        )
    
    async def agentic_search(
        self,
        query: str,
        strategies: Optional[List[str]] = None,
        auto_filter: bool = True,
        max_results: int = 50
    ) -> Dict[str, Any]:
        """
        Multi-strategy intelligent search orchestration.
        
        IMPLEMENTATION NOTE: Your Vector API doesn't have an /agentic-search endpoint.
        Your API client should implement this by:
        1. Using LLM with MCP tools to analyze the query and plan strategy
        2. Making multiple vector_search() calls with different parameters
        3. Optionally calling suggest_filters() for filter recommendations
        4. Combining and ranking results intelligently
        
        This method is a placeholder - replace with your implementation logic.
        """
        # Your API client implements this using LLM + multiple vector_search() calls
        # This is NOT a direct Vector API call
        raise NotImplementedError(
            "Your API client must implement this using LLM + multiple vector_search() calls. "
            "This is not a direct Vector API endpoint."
        )
    
    # =============================================================================
    # STATISTICS OPERATIONS - These map directly to your Vector API /api/stats/ endpoints
    # =============================================================================
    
    async def get_processing_stats(
        self,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processing statistics and system health metrics.
        MCP tool 'get_processing_stats' calls this for monitoring.
        """
        params = {}
        if project_id:
            params["project_id"] = project_id
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/stats/processing",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_project_details(self, project_id: str) -> Dict[str, Any]:
        """
        Detailed processing information for a specific project.
        MCP tool 'get_project_details' calls this for project analysis.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/stats/processing/{project_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_system_summary(self) -> Dict[str, Any]:
        """
        High-level system overview and health status.
        MCP tool 'get_system_summary' calls this for system monitoring.
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/stats/summary",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


# =============================================================================
# EXAMPLE USAGE IN YOUR API
# =============================================================================

class YourAPIService:
    """
    Example of how your API integrates the Vector API client
    with LLM recommendations from MCP server.
    
    Implementation Pattern:
    1. Direct API Tools: Call VectorAPIClient methods directly
    2. Intelligent Tools: Implement using LLM + multiple direct API calls
    """
    
    def __init__(self, vector_api_url: str, mcp_server_url: str):
        self.vector_client = VectorAPIClient(vector_api_url)
        self.mcp_server_url = mcp_server_url
    
    async def intelligent_search_endpoint(self, user_query: str) -> Dict[str, Any]:
        """
        Example: Implementing agentic_search using LLM + MCP + multiple Vector API calls
        """
        # 1. Get LLM recommendation using MCP tools
        llm_recommendation = await self.get_llm_recommendation(user_query)
        
        # 2. Execute based on recommendation
        if llm_recommendation["action"] == "vector_search":
            # Direct API call
            results = await self.vector_client.vector_search(
                query=llm_recommendation["parameters"]["query"],
                project_ids=llm_recommendation["parameters"].get("project_ids"),
                document_types=llm_recommendation["parameters"].get("document_types"),
            )
        elif llm_recommendation["action"] == "agentic_search":
            # Implement intelligent orchestration
            results = await self.implement_agentic_search(
                query=user_query,
                recommendation=llm_recommendation
            )
        
        return {
            "query": user_query,
            "results": results,
            "intelligence_used": True,
            "recommendation": llm_recommendation
        }
    
    async def implement_agentic_search(self, query: str, recommendation: Dict) -> Dict[str, Any]:
        """
        Your implementation of agentic_search using multiple Vector API calls
        """
        # Example implementation:
        # 1. Get filter suggestions using LLM + discovery tools
        # 2. Execute multiple vector_search calls with different strategies  
        # 3. Combine and rank results
        # 4. Return enhanced results
        
        # This is where you implement the intelligence that agentic_search provides
        pass
    
    async def get_llm_recommendation(self, query: str) -> Dict[str, Any]:
        """
        Placeholder for your LLM integration that uses MCP server.
        """
        # Your LLM integration code here
        # LLM has access to MCP tools and returns recommendations
        pass
