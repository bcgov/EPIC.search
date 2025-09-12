"""Ollama query validator implementation."""

import json
import logging
from typing import Dict, Any, Optional
from .ollama_client import OllamaClient
from ...abstractions.query_validator import QueryValidator

logger = logging.getLogger(__name__)


class OllamaQueryValidator(QueryValidator):
    """Ollama implementation of the query validator."""
    
    def __init__(self):
        """Initialize the Ollama query validator."""
        self.client = OllamaClient()
    
    def validate_query_relevance(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate if a query is relevant to EAO using Ollama.
        
        Args:
            query: The user's search query to validate.
            context: Optional additional context for validation.
            
        Returns:
            Dict containing validation results with keys:
            - is_relevant: Boolean indicating if query is relevant
            - confidence: Confidence score (0.0 to 1.0)
            - reasoning: List of reasons for the decision
            - recommendation: Recommendation for how to proceed
            - suggested_response: Optional response for irrelevant queries
            
        Raises:
            Exception: If validation fails.
        """
        try:
            # Build the validation prompt
            prompt = self._build_validation_prompt(context)
            
            # Define the function schema for structured output
            tools = [{
                "type": "function",
                "function": {
                    "name": "validate_query_relevance",
                    "description": "Validate if a query is relevant to EAO environmental assessments",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "is_relevant": {
                                "type": "boolean",
                                "description": "Whether the query is relevant to EAO scope"
                            },
                            "confidence": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score for the relevance assessment"
                            },
                            "reasoning": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of reasons for the relevance decision"
                            },
                            "recommendation": {
                                "type": "string",
                                "enum": ["proceed_with_search", "inform_user_out_of_scope"],
                                "description": "Recommendation for how to proceed"
                            },
                            "suggested_response": {
                                "type": "string",
                                "description": "Optional response message for irrelevant queries"
                            }
                        },
                        "required": ["is_relevant", "confidence", "reasoning", "recommendation"]
                    }
                }
            }]
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Validate this query: {query}"}
            ]
            
            logger.info("Validating query relevance using Ollama function calling")
            response = self.client.chat_completion(
                messages=messages,
                tools=tools,
                tool_choice="validate_query_relevance",
                temperature=0.1
            )
            
            # Parse the function call response
            choice = response["choices"][0]
            if choice["message"].get("tool_calls"):
                tool_call = choice["message"]["tool_calls"][0]
                validation_result = json.loads(tool_call["function"]["arguments"])
                
                # Validate and clean the result
                validation_result = self._validate_result(validation_result)
                
                logger.info(f"Query validation result: {validation_result}")
                return validation_result
            else:
                logger.warning("No function call in response, parsing content directly")
                return self._parse_content_response(choice["message"]["content"], query, context)
                
        except Exception as e:
            logger.error(f"Query validation failed: {str(e)}")
            # Return fallback validation
            return self._fallback_validation(query, context)
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "ollama"
    
    def _build_validation_prompt(self, context: Optional[str] = None) -> str:
        """Build the validation prompt."""
        prompt = """You are an expert at determining if search queries are relevant to the Environmental Assessment Office (EAO) of British Columbia.

The EAO's scope includes:
- Environmental assessments of major projects in BC
- Mining projects, LNG facilities, pipelines, infrastructure
- Environmental reviews and regulatory processes
- Wildlife and habitat assessments
- Indigenous consultation and engagement
- Environmental certificates and approvals
- Project compliance and monitoring

VALIDATION CRITERIA:
1. RELEVANT queries relate to:
   - Environmental assessments, projects, or processes
   - EAO-regulated industries (mining, energy, infrastructure)
   - Environmental impact studies or reports
   - Regulatory documents, permits, or certificates
   - Consultation processes or stakeholder engagement
   - Project names, locations, or companies in BC
   - Environmental monitoring or compliance
   - Even general searches that might find relevant content in EAO documents

2. IRRELEVANT queries are clearly about:
   - Non-environmental topics (sports, entertainment, recipes, etc.)
   - Areas completely outside BC environmental regulation
   - Personal questions unrelated to environmental assessment

IMPORTANT: When in doubt, err on the side of RELEVANT. Many queries that seem general might find useful information in EAO documents.

For IRRELEVANT queries, provide a helpful suggested_response directing users to ask about environmental assessments, projects, or EAO processes.

You must call the validate_query_relevance function with your assessment."""

        if context:
            prompt += f"\n\nAdditional context: {context}"
        
        return prompt
    
    def _validate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean the validation result."""
        # Ensure all required fields exist with defaults
        cleaned = {
            "is_relevant": result.get("is_relevant", True),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ["Unable to determine relevance"]),
            "recommendation": result.get("recommendation", "proceed_with_search"),
            "suggested_response": result.get("suggested_response")
        }
        
        # Ensure reasoning is a list
        if not isinstance(cleaned["reasoning"], list):
            cleaned["reasoning"] = [str(cleaned["reasoning"])]
        
        # Clamp confidence to valid range
        cleaned["confidence"] = max(0.0, min(1.0, cleaned["confidence"]))
        
        # Validate recommendation
        if cleaned["recommendation"] not in ["proceed_with_search", "inform_user_out_of_scope"]:
            cleaned["recommendation"] = "proceed_with_search"
        
        return cleaned
    
    def _parse_content_response(
        self, 
        content: str, 
        query: str, 
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse a content response that might contain JSON or structured data."""
        try:
            # Try to find JSON in the response
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            
            if start_idx != -1 and end_idx != -1:
                json_str = content[start_idx:end_idx + 1]
                parsed = json.loads(json_str)
                
                # If it looks like our expected structure, use it
                if isinstance(parsed, dict) and "is_relevant" in parsed:
                    return self._validate_result(parsed)
            
        except json.JSONDecodeError:
            pass
        
        # Fallback to simple content analysis
        return self._fallback_validation(query, context)
    
    def _fallback_validation(
        self,
        query: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Provide fallback validation when LLM fails."""
        # Simple keyword-based validation as fallback
        query_lower = query.lower()
        context_lower = context.lower() if context else ""
        full_text = f"{query_lower} {context_lower}".strip()
        
        # Key EAO/environmental terms
        eao_terms = [
            "environmental assessment", "eao", "environmental", "mining", "project",
            "assessment", "environmental review", "lng", "pipeline", "wildlife",
            "habitat", "consultation", "certificate", "approval", "british columbia"
        ]
        
        # Document and process terms common in EAO database
        rag_terms = [
            "certificate", "correspondence", "report", "document", "letter",
            "application", "submission", "consultation", "band", "nation",
            "indigenous", "first nations", "permit", "monitoring"
        ]
        
        # Clear non-EAO terms
        non_eao_terms = [
            "soccer", "football", "world cup", "movie", "music", "recipe",
            "shopping", "celebrity", "iphone", "restaurant", "vacation",
            "gaming", "netflix", "instagram", "facebook"
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
            reasoning = ["Environmental/EAO keywords detected", "Query appears relevant to EAO scope"]
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
            reasoning = ["Short query detected - allowing for database search", 
                        "Short queries may reference specific content in EAO documents"]
            recommendation = "proceed_with_search"
            suggested_response = None
        else:
            # Default to allowing for search
            is_relevant = True
            confidence = 0.4
            reasoning = ["Allowing query for database search", "Query may reference content within EAO documents"]
            recommendation = "proceed_with_search"
            suggested_response = None
        
        return {
            "is_relevant": is_relevant,
            "confidence": confidence,
            "reasoning": reasoning,
            "recommendation": recommendation,
            "suggested_response": suggested_response
        }