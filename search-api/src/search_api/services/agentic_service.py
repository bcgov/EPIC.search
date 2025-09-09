"""Agentic Service - Orchestrates LLM interactions through MCP Server.

This service provides the intelligent layer that uses the MCP server to orchestrate
complex search workflows. It implements the three key agentic methods that were
identified as needing LLM integration.
"""

from typing import Dict, Any, List, Optional
from flask import current_app
from ..clients.mcp_client import get_mcp_client_safe, ensure_mcp_connection, call_mcp_tool_with_retry

class AgenticService:
    """Service for agentic workflow orchestration using MCP server."""
    
    @staticmethod
    def list_tools() -> Optional[List[Dict[str, Any]]]:
        """List available MCP tools for health checking.
        
        Returns:
            List of available tools or None if MCP server unavailable
        """
        try:
            client = get_mcp_client_safe()
            if client is None:
                current_app.logger.warning("MCP client unavailable for tools listing")
                return None
                
            # Send tools/list request to MCP server
            tools_request = {
                "jsonrpc": "2.0",
                "id": "tools-list",
                "method": "tools/list",
                "params": {}
            }
            
            response = client.send_request(tools_request)
            if response and 'result' in response and 'tools' in response['result']:
                tools = response['result']['tools']
                current_app.logger.info(f"Listed {len(tools)} MCP tools")
                return tools
            else:
                current_app.logger.warning("Invalid response from MCP server for tools/list")
                return None
                
        except Exception as e:
            current_app.logger.error(f"Error listing MCP tools: {e}")
            return None
    
    @staticmethod
    def get_mcp_status() -> Dict[str, Any]:
        """Get MCP server connection status and available tools.
        
        Returns:
            dict: Status information including connection state and available tools
        """
        try:
            current_app.logger.info("=== Getting MCP status ===")
            
            ensure_mcp_connection()
            mcp_client = get_mcp_client_safe()
            
            if not mcp_client:
                return {
                    "connected": False,
                    "error": "MCP client unavailable",
                    "tools": [],
                    "tool_count": 0
                }
            
            # Get connection status
            connected = mcp_client.is_connected
            
            # Get available tools
            tools = mcp_client.get_available_tools() if connected else []
            tool_count = len(tools) if tools else 0
            
            current_app.logger.info(f"MCP connected: {connected}, tools: {tool_count}")
            
            return {
                "connected": connected,
                "tools": tools,
                "tool_count": tool_count,
                "server_info": {
                    "name": "EPIC Search MCP Server",
                    "version": "1.0.0"
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting MCP status: {e}")
            return {
                "connected": False,
                "error": str(e),
                "tools": [],
                "tool_count": 0
            }
    
    @staticmethod
    def _fallback_suggest_filters(query: str) -> Dict[str, Any]:
        """Fallback filter suggestions when MCP server is unavailable."""
        return {
            "result": {
                "recommended_filters": {
                    "search_strategy": "HYBRID_SEMANTIC_FALLBACK",
                    "project_ids": [],
                    "document_type_ids": []
                },
                "confidence": 0.1,
                "reasoning": "Fallback recommendation - MCP server unavailable"
            },
            "metrics": {
                "method": "suggest_filters",
                "mcp_tools_used": [],
                "fallback_used": True,
                "error": "MCP server unavailable"
            }
        }
    
    @staticmethod
    def suggest_filters(query: str, context: str = None) -> Dict[str, Any]:
        """AI-powered filter recommendations based on query analysis.
        
        Uses MCP server to analyze the query and recommend appropriate filters
        for projects, document types, and search strategies.
        
        Args:
            query: The user's search query
            context: Additional context about the search intent
            
        Returns:
            dict: Filter recommendations with confidence scores
        """
        try:
            current_app.logger.info(f"=== Agentic suggest_filters started ===")
            current_app.logger.info(f"Query: {query}")
            current_app.logger.info(f"Context: {context}")
            
            ensure_mcp_connection()
            
            # Use MCP server to get intelligent filter recommendations with retry
            current_app.logger.info("Getting intelligent filter recommendations from MCP server...")
            
            filter_context = {
                "query": query,
                "context": context or "General search intent"
            }
            
            result = call_mcp_tool_with_retry("suggest_filters", filter_context)
            
            current_app.logger.info(f"MCP suggest_filters raw result: {result}")
            
            # Parse the MCP result format which comes as content array with text
            parsed_result = {}
            if result and isinstance(result, dict) and 'content' in result:
                content = result['content']
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get('text', '{}')
                    try:
                        import json
                        parsed_result = json.loads(text_content)
                        current_app.logger.info(f"Parsed MCP result: {parsed_result}")
                    except json.JSONDecodeError as e:
                        current_app.logger.error(f"Failed to parse MCP JSON response: {e}")
                        parsed_result = {}
            
            # Transform MCP result format to expected format
            if parsed_result and isinstance(parsed_result, dict):
                # Extract the suggested filters from MCP response
                suggested_filters = parsed_result.get("suggested_filters", {})
                
                # Map MCP format to expected format
                recommended_filters = {
                    "project_ids": suggested_filters.get("projectIds", []),
                    "document_type_ids": suggested_filters.get("documentTypeIds", []),
                    "search_strategy": parsed_result.get("recommended_search_strategy", "HYBRID_SEMANTIC_FALLBACK")
                }
                
                # Add semantic query if provided (cleaned query for better vector search)
                if "semanticQuery" in suggested_filters:
                    recommended_filters["semantic_query"] = suggested_filters["semanticQuery"]
                
                # Add date range if provided
                if "dateRange" in suggested_filters:
                    recommended_filters["date_range"] = suggested_filters["dateRange"]
                
                current_app.logger.info(f"Transformed recommended filters: {recommended_filters}")
                
                return {
                    "result": {
                        "recommended_filters": recommended_filters,
                        "confidence": parsed_result.get("confidence", 0.8),
                        "entities_detected": parsed_result.get("entities_detected", []),
                        "recommendations": parsed_result.get("recommendations", []),
                        "reasoning": parsed_result.get("reasoning", "MCP analysis completed")
                    },
                    "metrics": {
                        "method": "suggest_filters",
                        "mcp_tools_used": ["suggest_filters"],
                        "reasoning_provided": True
                    }
                }
            else:
                current_app.logger.warning("Empty or invalid parsed MCP result")
                return AgenticService._fallback_suggest_filters(query)
                      
        except Exception as e:
            current_app.logger.error(f"Error in suggest_filters: {str(e)}")
            # Fallback to basic recommendations
            return {
                "result": {
                    "recommended_filters": {
                        "search_strategy": "HYBRID_SEMANTIC_FALLBACK",
                        "project_ids": [],
                        "document_type_ids": []
                    },
                    "confidence": 0.1,
                    "reasoning": f"Fallback recommendation due to error: {str(e)}"
                },
                "metrics": {
                    "method": "suggest_filters",
                    "mcp_tools_used": [],
                    "fallback_used": True,
                    "error": str(e)
                }
            }
    
    @staticmethod
    def suggest_search_strategy(query: str, context: str = None, user_intent: str = "find_documents") -> Dict[str, Any]:
        """AI-powered search strategy recommendations based on query analysis.
        
        Uses MCP server to analyze the query characteristics and recommend the optimal
        search strategy for the vector search API.
        
        Args:
            query: The user's search query
            context: Additional context about the search intent
            user_intent: The user's intent (e.g., 'find_documents', 'explore_topic', 'specific_lookup')
            
        Returns:
            dict: Search strategy recommendation with confidence scores and explanation
        """
        try:
            current_app.logger.info(f"=== Agentic suggest_search_strategy started ===")
            current_app.logger.info(f"Query: {query}")
            current_app.logger.info(f"Context: {context}")
            current_app.logger.info(f"User intent: {user_intent}")
            
            ensure_mcp_connection()
            
            # Use MCP server to get intelligent search strategy recommendation with retry
            current_app.logger.info("Getting intelligent search strategy recommendation from MCP server...")
            
            strategy_context = {
                "query": query,
                "context": context or "General search context",
                "user_intent": user_intent
            }
            
            result = call_mcp_tool_with_retry("suggest_search_strategy", strategy_context)
            
            current_app.logger.info(f"MCP suggest_search_strategy raw result: {result}")
            
            # Parse the MCP result format which comes as content array with text
            parsed_result = {}
            if result and isinstance(result, dict) and 'content' in result:
                content = result['content']
                if isinstance(content, list) and len(content) > 0:
                    text_content = content[0].get('text', '{}')
                    try:
                        import json
                        parsed_result = json.loads(text_content)
                        current_app.logger.info(f"Parsed MCP strategy result: {parsed_result}")
                    except json.JSONDecodeError as e:
                        current_app.logger.error(f"Failed to parse MCP JSON response: {e}")
                        parsed_result = {}
            
            # Extract strategy recommendation from MCP response
            if parsed_result and isinstance(parsed_result, dict):
                recommended_strategy = parsed_result.get("recommended_strategy", "HYBRID_SEMANTIC_FALLBACK")
                confidence = parsed_result.get("confidence", 0.7)
                explanation = parsed_result.get("explanation", "Strategy recommended by AI analysis")
                alternatives = parsed_result.get("alternative_strategies", [])
                
                current_app.logger.info(f"Recommended strategy: {recommended_strategy} (confidence: {confidence})")
                
                return {
                    "result": {
                        "recommended_strategy": recommended_strategy,
                        "confidence": confidence,
                        "explanation": explanation,
                        "alternative_strategies": alternatives,
                        "query": query,
                        "user_intent": user_intent
                    },
                    "metrics": {
                        "method": "suggest_search_strategy",
                        "mcp_tools_used": ["suggest_search_strategy"],
                        "strategy_recommended": True
                    }
                }
            else:
                current_app.logger.warning("Empty or invalid parsed MCP strategy result")
                return AgenticService._fallback_suggest_search_strategy(query, user_intent)
                      
        except Exception as e:
            current_app.logger.error(f"Error in suggest_search_strategy: {str(e)}")
            return AgenticService._fallback_suggest_search_strategy(query, user_intent)

    @staticmethod
    def _fallback_suggest_search_strategy(query: str, user_intent: str = "find_documents") -> Dict[str, Any]:
        """Fallback search strategy suggestions when MCP server is unavailable."""
        current_app.logger.info("Using fallback search strategy logic - defaulting to HYBRID_SEMANTIC_FALLBACK")
        
        # When MCP is unavailable, always use HYBRID_SEMANTIC_FALLBACK as the safest option
        # This provides both keyword and semantic capabilities without requiring MCP intelligence
        strategy = "HYBRID_SEMANTIC_FALLBACK"
        explanation = "MCP server unavailable, using hybrid approach as fallback for balanced results"
        
        # For specific cases where we can be confident without MCP
        query_lower = query.lower()
        
        # Only override for very specific patterns we can handle confidently
        if any(pattern in query_lower for pattern in ['id:', 'number:', 'code:', '#']) and len(query.split()) <= 3:
            strategy = "KEYWORD_ONLY"
            explanation = "Detected specific identifiers, using keyword matching"
        elif user_intent == "specific_lookup" and len(query.split()) <= 2:
            strategy = "KEYWORD_ONLY"
            explanation = "Specific lookup intent with short query, prioritizing keyword matching"
        
        return {
            "result": {
                "recommended_strategy": strategy,
                "confidence": 0.6,
                "explanation": explanation,
                "alternative_strategies": ["HYBRID_SEMANTIC_FALLBACK", "KEYWORD_ONLY", "SEMANTIC_ONLY"],
                "query": query,
                "user_intent": user_intent
            },
            "metrics": {
                "method": "suggest_search_strategy",
                "mcp_tools_used": [],
                "fallback_used": True
            }
        }

    @staticmethod
    def check_query_relevance(query: str, context: str = None) -> Dict[str, Any]:
        """Check if a query is relevant to EAO using MCP tools.
        
        Args:
            query (str): The user query to check for EAO relevance
            context (str, optional): Additional context for the query
            
        Returns:
            Dict containing:
                - result: Contains is_eao_relevant, confidence, reasoning, recommendation
                - metrics: Contains method info and MCP tool usage
        """
        try:
            current_app.logger.info(f"Checking query relevance for: {query[:100]}...")
            
            # Ensure MCP connection is available
            ensure_mcp_connection()
            
            # Prepare arguments for MCP tool call
            tool_args = {"query": query}
            if context:
                tool_args["context"] = context
            
            # Use retry method for consistency
            result = call_mcp_tool_with_retry("check_query_relevance", tool_args)
            
            if result and 'content' in result:
                mcp_result = result['content'][0].get('text', {})
                
                if isinstance(mcp_result, str):
                    # If it's a string, try to parse it
                    import json
                    try:
                        mcp_result = json.loads(mcp_result)
                    except json.JSONDecodeError:
                        current_app.logger.warning("Failed to parse MCP response as JSON")
                        return AgenticService._check_query_relevance_fallback(query, context)
                
                # Extract relevance information
                is_relevant = mcp_result.get('is_eao_relevant', True)
                confidence = mcp_result.get('confidence', 0.5)
                reasoning = mcp_result.get('reasoning', [])
                recommendation = mcp_result.get('recommendation', 'proceed_with_search')
                suggested_response = mcp_result.get('suggested_response', None)
                
                current_app.logger.info(f"Query relevance check via MCP - Relevant: {is_relevant}, Confidence: {confidence}")
                
                return {
                    "result": {
                        "is_eao_relevant": is_relevant,
                        "confidence": confidence,
                        "reasoning": reasoning,
                        "recommendation": recommendation,
                        "suggested_response": suggested_response,
                        "query": query
                    },
                    "metrics": {
                        "method": "check_query_relevance",
                        "mcp_tools_used": ["check_query_relevance"],
                        "fallback_used": False
                    }
                }
            else:
                current_app.logger.warning("Invalid response from MCP check_query_relevance tool")
                return AgenticService._check_query_relevance_fallback(query, context)
                
        except Exception as e:
            current_app.logger.error(f"Error during MCP query relevance check: {e}")
            return AgenticService._check_query_relevance_fallback(query, context)
    
    @staticmethod
    def _check_query_relevance_fallback(query: str, context: str = None) -> Dict[str, Any]:
        """Fallback query relevance check when MCP tools are unavailable."""
        current_app.logger.info(f"Using fallback query relevance check for: {query[:100]}...")
        
        # Simple keyword-based relevance check with RAG-aware logic
        query_lower = query.lower()
        context_lower = context.lower() if context else ""
        full_text = f"{query_lower} {context_lower}".strip()
        
        # Key EAO/environmental terms
        eao_terms = [
            "environmental assessment", "eao", "environmental", "mining", "project",
            "assessment", "environmental review", "lng", "pipeline", "wildlife",
            "habitat", "consultation", "certificate", "approval", "british columbia"
        ]
        
        # Document and process terms common in EAO RAG database
        rag_terms = [
            "certificate", "correspondence", "report", "document", "letter",
            "application", "submission", "consultation", "band", "nation",
            "indigenous", "first nations", "tax", "agreement", "permit"
        ]
        
        # Clear non-EAO terms
        non_eao_terms = [
            "soccer", "football", "world cup", "movie", "music", "recipe",
            "shopping", "celebrity", "iphone", "restaurant", "vacation"
        ]
        
        eao_matches = sum(1 for term in eao_terms if term in full_text)
        rag_matches = sum(1 for term in rag_terms if term in full_text)
        non_eao_matches = sum(1 for term in non_eao_terms if term in query_lower)
        
        # Check for short query patterns
        is_short_query = len(query.split()) <= 3
        has_capital_letters = any(c.isupper() for c in query)
        
        if non_eao_matches > 0 and eao_matches == 0 and rag_matches == 0 and not is_short_query:
            # Clear non-EAO query with no environmental or document context
            is_relevant = False
            confidence = 0.8
            reasoning = ["Non-EAO query detected", "No environmental or document-related keywords found"]
            recommendation = "inform_user_out_of_scope"
            suggested_response = "I'm designed to help with Environmental Assessment Office (EAO) related queries about environmental assessments, projects, and regulatory processes in British Columbia. Your question appears to be outside this scope. Please ask about environmental assessments, projects under review, or EAO processes."
        elif eao_matches > 0:
            # Contains EAO keywords
            is_relevant = True
            confidence = min(0.8, 0.5 + (eao_matches * 0.1))
            reasoning = [f"Environmental/EAO keywords detected", "Query appears relevant to EAO scope"]
            recommendation = "proceed_with_search"
            suggested_response = None
        elif rag_matches > 0:
            # Contains document/process terms
            is_relevant = True
            confidence = 0.7
            reasoning = ["Document/process terms detected", "Query appears to be searching for EAO-related documents"]
            recommendation = "proceed_with_search"
            suggested_response = None
        elif is_short_query:
            # Short queries are often proper nouns or specific search terms
            is_relevant = True
            confidence = 0.6 if has_capital_letters else 0.5
            reasoning = ["Short query detected - allowing for RAG database search", 
                        "Short queries may reference specific content in EAO documents"]
            recommendation = "proceed_with_search"
            suggested_response = None
        else:
            # Default to allowing for RAG search
            is_relevant = True
            confidence = 0.4
            reasoning = ["Allowing query for RAG database search", "Query may reference content within EAO documents"]
            recommendation = "proceed_with_search"
            suggested_response = None
        
        return {
            "result": {
                "is_eao_relevant": is_relevant,
                "confidence": confidence,
                "reasoning": reasoning,
                "recommendation": recommendation,
                "suggested_response": suggested_response,
                "query": query
            },
            "metrics": {
                "method": "check_query_relevance",
                "mcp_tools_used": [],
                "fallback_used": True
            }
        }
