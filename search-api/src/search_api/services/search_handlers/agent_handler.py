"""
Agent Handler

Handles Agent mode processing - complete query processing via agent stub.
"""
import time
from typing import Dict, List, Optional, Any
from flask import current_app

from .base_handler import BaseSearchHandler


class AgentHandler(BaseSearchHandler):
    """Handler for Agent mode processing - complete query processing via agent stub."""
    
    @classmethod
    def handle(cls, query: str, project_ids: Optional[List[str]] = None, 
               document_type_ids: Optional[List[str]] = None, 
               search_strategy: Optional[str] = None, 
               inference: Optional[List] = None, 
               ranking: Optional[Dict] = None, 
               metrics: Optional[Dict] = None,
               user_location: Optional[Dict] = None,
               location: Optional[Dict] = None, 
               project_status: Optional[str] = None, 
               years: Optional[List] = None) -> Dict[str, Any]:
        """Handle agent mode processing - complete query processing via agent stub.
        
        Agent mode delegates the entire query processing to the agent stub, which handles:
        - Multi-step reasoning and planning
        - Multiple RAG calls with different strategies  
        - Result consolidation and deduplication
        - Tool suggestions for API improvements
        
        Args:
            query: The user query
            project_ids: Optional user-provided project IDs
            document_type_ids: Optional user-provided document type IDs  
            search_strategy: Optional user-provided search strategy
            inference: Inference settings
            ranking: Optional ranking configuration
            metrics: Metrics dictionary to update
            user_location: Optional user location data
            location: Optional location parameter (user-provided takes precedence)
            project_status: Optional project status parameter (user-provided takes precedence)
            years: Optional years parameter (user-provided takes precedence)
            
        Returns:
            Complete response dictionary with agent results and summary
        """
        start_time = time.time()
        current_app.logger.info("🤖 AGENT MODE: Starting complete agent processing...")
        
        try:
            # Call agent stub with all user-provided parameters
            from search_api.services.search_handlers.agent.agent_stub import handle_agent_query
            from search_api.services.generation.factories import LLMClientFactory
            
            # Create LLM client for agent planning
            llm_client = LLMClientFactory.create_client()
            
            agent_result = handle_agent_query(
                query=query,
                reason="Agent mode requested",
                llm_client=llm_client,
                user_location=user_location,
                project_ids=project_ids,
                document_type_ids=document_type_ids,
                search_strategy=search_strategy,
                ranking=ranking,
                location=location,
                project_status=project_status,
                years=years
            )
            
            current_app.logger.info("🤖 AGENT MODE: Agent processing completed successfully")
            
            # Handle validation failure - return early with suggested response
            if agent_result and agent_result.get("validation_failed", False):
                current_app.logger.info("🤖 AGENT MODE: Query validation failed - returning early response")
                total_time = round((time.time() - start_time) * 1000, 2)
                metrics["total_time_ms"] = total_time
                metrics["agent_processing_time_ms"] = total_time
                metrics["agent_stub_called"] = True
                metrics["validation_failed"] = True
                metrics["validation_result"] = agent_result.get("validation_result", {})
                
                return {
                    "result": {
                        "response": agent_result.get("suggested_response", "This query appears to be outside the scope of EAO's mandate. Please ask about environmental assessments, projects, or regulatory processes in British Columbia."),
                        "documents": [],
                        "document_chunks": [],
                        "metrics": metrics,
                        "search_quality": "not_applicable",
                        "project_inference": {},
                        "document_type_inference": {},
                        "early_exit": True,
                        "exit_reason": "query_not_relevant_by_agent_validation"
                    }
                }
            
            # Update metrics with streamlined agent results
            metrics["agent_processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
            metrics["agent_stub_called"] = True
            
            # Add streamlined agent execution info
            if agent_result:
                # Execution plan (keep as is)
                metrics["execution_plan"] = agent_result.get("execution_plan", [])
                
                # Execution summary with counts
                execution_summary = agent_result.get("execution_summary", {})
                tool_executions = agent_result.get("tool_executions", [])
                
                # Count search executions for consolidation info
                search_count = len([exec for exec in tool_executions if exec.get("tool") == "search"])
                successful_searches = len([exec for exec in tool_executions if exec.get("tool") == "search" and exec.get("result", {}).get("success")])
                
                metrics["agent_execution"] = {
                    "total_steps": execution_summary.get("total_steps", 0),
                    "successful_steps": execution_summary.get("successful_steps", 0), 
                    "failed_steps": execution_summary.get("failed_steps", 0),
                    "search_executions": search_count,
                    "successful_searches": successful_searches
                }
                
                # Consolidation info (only if multiple searches)
                if search_count > 1:
                    consolidated_results = agent_result.get("consolidated_results", {})
                    metrics["agent_consolidation"] = {
                        "multiple_searches_performed": True,
                        "total_documents_consolidated": consolidated_results.get("total_documents", 0),
                        "total_chunks_consolidated": consolidated_results.get("total_chunks", 0)
                    }
                
                # Execution summary - what was actually executed
                tool_executions = agent_result.get("tool_executions", [])
                executed_steps = []
                for execution in tool_executions:
                    step_summary = {
                        "step": execution.get("step"),
                        "tool": execution.get("tool"),
                        "parameters": execution.get("parameters", {}),
                        "success": execution.get("result", {}).get("success", False)
                    }
                    # Add execution mode if present
                    if execution.get("execution_mode"):
                        step_summary["execution_mode"] = execution.get("execution_mode")
                    # Add skipped flag if present
                    if execution.get("result", {}).get("skipped"):
                        step_summary["skipped"] = True
                    executed_steps.append(step_summary)
                
                if executed_steps:
                    metrics["steps_executed"] = executed_steps
                
                # Tool suggestions (LLM generates up to 3)
                tool_suggestions = agent_result.get("tool_suggestions", [])
                if tool_suggestions:
                    metrics["tool_suggestions"] = tool_suggestions
            
            # Extract consolidated results from agent
            agent_documents = []
            agent_document_chunks = []
            
            # The agent stub returns consolidated results in its response
            if agent_result and "consolidated_results" in agent_result:
                consolidated = agent_result["consolidated_results"]
                agent_documents = consolidated.get("documents", [])
                agent_document_chunks = consolidated.get("document_chunks", [])
                
                current_app.logger.info(f"🤖 AGENT MODE: Agent returned {len(agent_documents)} documents and {len(agent_document_chunks)} chunks")
            
            # Use agent-generated summary if available, otherwise generate fallback
            if agent_result and "summary_result" in agent_result:
                # Agent performed summarization as part of its execution plan
                summary_result = agent_result["summary_result"]
                final_response = summary_result.get("summary", "No summary available")
                current_app.logger.info("🤖 AGENT MODE: Using agent-generated summary")
                
                # Add agent summary metadata to metrics
                metrics["summary_generated"] = True
                metrics["summary_method"] = summary_result.get("method", "agent_execution")
                metrics["summary_confidence"] = summary_result.get("confidence", 0.0)
                metrics["summary_provider"] = summary_result.get("provider", "agent_stub")
                metrics["summary_model"] = summary_result.get("model", "unknown")
                
            else:
                # Fallback: generate summary if agent didn't include summarization step
                current_app.logger.info("🤖 AGENT MODE: Agent summary not available, generating fallback summary...")
                
                try:
                    from search_api.services.generation.factories import SummarizerFactory
                    
                    summarizer = SummarizerFactory.create_summarizer()
                    
                    # Combine documents and chunks for summarization
                    all_results = agent_documents + agent_document_chunks
                    
                    if all_results:
                        summary_result = summarizer.summarize_search_results(query, all_results)
                        final_response = summary_result.get("summary", "No summary available")
                        current_app.logger.info("🤖 AGENT MODE: Fallback AI summary generated successfully")
                    else:
                        final_response = "The agent processing completed but no relevant documents were found."
                        current_app.logger.info("🤖 AGENT MODE: No results to summarize")
                        
                    metrics["summary_generated"] = True
                    metrics["summary_method"] = "fallback_generation"
                    
                except Exception as e:
                    current_app.logger.error(f"🤖 AGENT MODE: Fallback summary generation failed: {e}")
                    final_response = "The agent found relevant information but summary generation failed."
                    metrics["summary_error"] = str(e)
            
            # Calculate final metrics
            total_time = round((time.time() - start_time) * 1000, 2)
            metrics["total_time_ms"] = total_time
            
            # Return complete response (without full agent_result to avoid duplication)
            return {
                "result": {
                    "response": final_response,
                    "documents": agent_documents,
                    "document_chunks": agent_document_chunks,
                    "metrics": metrics,
                    "search_quality": "agent_processed",
                    "project_inference": {},
                    "document_type_inference": {},
                    "agent_processing": True
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"🤖 AGENT MODE: Agent processing failed: {e}")
            metrics["agent_fallback"] = True
            metrics["agent_error"] = str(e)
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            
            # Return error response - fallback will be handled at higher level if needed
            return {
                "result": {
                    "response": "An error occurred while processing your request with the agent. Please try again.",
                    "documents": [],
                    "document_chunks": [],
                    "metrics": metrics,
                    "search_quality": "error",
                    "project_inference": {},
                    "document_type_inference": {},
                    "agent_processing": False,
                    "error": True
                }
            }