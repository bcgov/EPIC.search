"""Stub for agent-based query processing."""

import logging

logger = logging.getLogger(__name__)


def handle_agent_query(query: str, reason: str) -> dict:
    """Stub for handling agent-required queries.
    
    Args:
        query: The complex query that requires agent processing
        reason: Why the query was classified as agent-required
        
    Returns:
        Dict indicating agent processing was attempted but not implemented
    """
    
    logger.info("=" * 50)
    logger.info("AGENT QUERY DETECTED")
    logger.info(f"Query: {query}")
    logger.info(f"Reason: {reason}")
    logger.info("Agent processing not yet implemented - falling back to normal flow")
    logger.info("=" * 50)
    
    return {
        "agent_attempted": True,
        "agent_implemented": False,
        "query": query,
        "reason": reason,
        "fallback_to_normal_flow": True
    }