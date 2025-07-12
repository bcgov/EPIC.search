"""Main inference pipeline for processing search queries.

This module provides the main InferencePipeline class that orchestrates
intelligent inference of project IDs and document type IDs from natural
language search queries. The pipeline processes queries sequentially,
applying each inference step and maintaining detailed metadata about
the processing workflow.

The pipeline architecture:
1. Input validation and preprocessing
2. Project inference (when no explicit project IDs provided)
3. Document type inference (when no explicit document type IDs provided)
4. Query cleaning and normalization
5. Metadata collection and response formatting

Each step is designed to be transparent, providing detailed reasoning
and confidence scores for the inference decisions made.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional

class InferencePipeline:
    """Main inference pipeline for processing search queries with intelligent context detection.
    
    This class orchestrates the inference workflow, applying project and document type
    inference sequentially while maintaining detailed metadata about each step.
    """
    
    def __init__(self):
        """Initialize the inference pipeline with default configuration."""
        self.project_confidence_threshold = 0.8
        self.document_type_confidence_threshold = 0.7
        
    def process_query(
        self,
        query: str,
        project_ids: Optional[List[str]] = None,
        document_type_ids: Optional[List[str]] = None,
        skip_generic_cleaning: bool = False,
        run_project_inference: bool = True,
        run_document_type_inference: bool = True
    ) -> Dict[str, Any]:
        """Process a search query through the complete inference pipeline.
        
        Args:
            query (str): The natural language search query
            project_ids (Optional[List[str]]): Explicit project IDs (skips project inference if provided)
            document_type_ids (Optional[List[str]]): Explicit document type IDs (skips doc type inference if provided)
            skip_generic_cleaning (bool): Whether to skip query cleaning for generic requests
            run_project_inference (bool): Whether to run project inference (default: True)
            run_document_type_inference (bool): Whether to run document type inference (default: True)
            
        Returns:
            Dict[str, Any]: Complete inference results including:
                - final_query: The processed query after all inference steps
                - inferred_project_ids: List of inferred project IDs (if any)
                - inferred_document_type_ids: List of inferred document type IDs (if any)
                - project_inference_metadata: Detailed project inference metadata
                - document_type_inference_metadata: Detailed document type inference metadata
                - processing_summary: High-level summary of what was inferred
        """
        # Import services here to avoid circular imports
        from .project_inference import project_inference_service
        from .document_type_inference import document_type_inference_service
        from ..vector_search import is_generic_document_request
        
        # Initialize processing state
        processing_state = {
            "original_query": query,
            "current_query": query,
            "project_cleaned_query": query,
            "doc_type_cleaned_query": query,
            "final_query": query,
            "inferred_project_ids": [],
            "inferred_document_type_ids": [],
            "project_inference_metadata": None,
            "document_type_inference_metadata": None,
            "project_confidence": 0.0,
            "document_type_confidence": 0.0,
            "steps_applied": []
        }
        
        # Check if this is a generic request that should skip cleaning
        is_generic_request = skip_generic_cleaning or is_generic_document_request(query)
        
        # Step 1: Project inference (if no explicit project IDs provided and inference is enabled)
        if (not project_ids or (isinstance(project_ids, list) and len(project_ids) == 0)) and run_project_inference:
            logging.info(f"Starting project inference for query: '{query}'")
            project_results = self._process_project_inference(
                processing_state, is_generic_request
            )
            if project_results["applied"]:
                project_ids = project_results["inferred_project_ids"]
                processing_state.update(project_results)
        elif not run_project_inference:
            logging.info("Project inference disabled by inference parameter")
        else:
            logging.info(f"Skipping project inference: explicit project IDs provided: {project_ids}")
            
        # Step 2: Document type inference (if no explicit document type IDs provided and inference is enabled)
        if (not document_type_ids or (isinstance(document_type_ids, list) and len(document_type_ids) == 0)) and run_document_type_inference:
            logging.info(f"Starting document type inference for query: '{processing_state['current_query']}'")
            doc_type_results = self._process_document_type_inference(
                processing_state, is_generic_request
            )
            if doc_type_results["applied"]:
                document_type_ids = doc_type_results["inferred_document_type_ids"]
                processing_state.update(doc_type_results)
        elif not run_document_type_inference:
            logging.info("Document type inference disabled by inference parameter")
        else:
            logging.info(f"Skipping document type inference: explicit document type IDs provided: {document_type_ids}")
            
        # Finalize processing state
        processing_state["final_query"] = processing_state["current_query"]
        
        # Build comprehensive response
        return self._build_inference_response(
            processing_state, project_ids, document_type_ids
        )
        
    def _process_project_inference(
        self, 
        processing_state: Dict[str, Any], 
        is_generic_request: bool
    ) -> Dict[str, Any]:
        """Process project inference step.
        
        Args:
            processing_state (Dict[str, Any]): Current processing state
            is_generic_request (bool): Whether this is a generic request
            
        Returns:
            Dict[str, Any]: Project inference results
        """
        from .project_inference import project_inference_service
        
        # Perform project inference
        inferred_project_ids, project_confidence, project_metadata = project_inference_service.infer_projects_from_query(
            processing_state["original_query"]
        )
        
        result = {
            "inferred_project_ids": inferred_project_ids or [],
            "project_confidence": project_confidence,
            "project_inference_metadata": project_metadata,
            "applied": False
        }
        
        # Apply project inference if confidence meets threshold
        if inferred_project_ids and project_confidence > self.project_confidence_threshold:
            result["applied"] = True
            
            # Clean query unless it's a generic request
            if not is_generic_request:
                project_cleaned = project_inference_service.clean_query_after_inference(
                    processing_state["current_query"], project_metadata
                )
                processing_state["project_cleaned_query"] = project_cleaned
                processing_state["current_query"] = project_cleaned
                processing_state["steps_applied"].append("project_cleaning")
                
                logging.info(f"Project inference applied: {inferred_project_ids} with confidence {project_confidence:.3f}")
                logging.info(f"Query after project cleaning: '{project_cleaned}'")
            else:
                processing_state["project_cleaned_query"] = processing_state["current_query"]
                logging.info(f"Project inference applied but skipped cleaning for generic request")
                
        else:
            logging.info(f"Project inference not applied: confidence {project_confidence:.3f} below threshold {self.project_confidence_threshold}")
            
        return result
        
    def _process_document_type_inference(
        self, 
        processing_state: Dict[str, Any], 
        is_generic_request: bool
    ) -> Dict[str, Any]:
        """Process document type inference step.
        
        Args:
            processing_state (Dict[str, Any]): Current processing state
            is_generic_request (bool): Whether this is a generic request
            
        Returns:
            Dict[str, Any]: Document type inference results
        """
        from .document_type_inference import document_type_inference_service
        
        # Use the current query state (after project cleaning)
        query_for_inference = processing_state["current_query"]
        
        # Perform document type inference
        inferred_doc_type_ids, doc_type_confidence, doc_type_metadata = document_type_inference_service.infer_document_types_from_query(
            query_for_inference
        )
        
        result = {
            "inferred_document_type_ids": inferred_doc_type_ids or [],
            "document_type_confidence": doc_type_confidence,
            "document_type_inference_metadata": doc_type_metadata,
            "applied": False
        }
        
        # Apply document type inference if confidence meets threshold
        if inferred_doc_type_ids and doc_type_confidence > self.document_type_confidence_threshold:
            result["applied"] = True
            
            # Clean query unless it's a generic request
            if not is_generic_request:
                doc_type_cleaned = document_type_inference_service.clean_query_after_inference(
                    processing_state["current_query"], doc_type_metadata
                )
                processing_state["doc_type_cleaned_query"] = doc_type_cleaned
                processing_state["current_query"] = doc_type_cleaned
                processing_state["steps_applied"].append("document_type_cleaning")
                
                logging.info(f"Document type inference applied: {inferred_doc_type_ids} with confidence {doc_type_confidence:.3f}")
                logging.info(f"Query after document type cleaning: '{doc_type_cleaned}'")
            else:
                processing_state["doc_type_cleaned_query"] = processing_state["current_query"]
                logging.info(f"Document type inference applied but skipped cleaning for generic request")
                
        else:
            logging.info(f"Document type inference not applied: confidence {doc_type_confidence:.3f} below threshold {self.document_type_confidence_threshold}")
            
        return result
        
    def _build_inference_response(
        self, 
        processing_state: Dict[str, Any], 
        final_project_ids: Optional[List[str]], 
        final_document_type_ids: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Build the final inference response with all metadata.
        
        Args:
            processing_state (Dict[str, Any]): Complete processing state
            final_project_ids (Optional[List[str]]): Final project IDs to use
            final_document_type_ids (Optional[List[str]]): Final document type IDs to use
            
        Returns:
            Dict[str, Any]: Complete inference response
        """
        response = {
            "query_processing": {
                "original_query": processing_state["original_query"],
                "final_query": processing_state["final_query"],
                "steps_applied": processing_state["steps_applied"],
                "query_changed": processing_state["final_query"] != processing_state["original_query"]
            },
            "project_inference": {
                "attempted": processing_state["project_inference_metadata"] is not None,
                "applied": bool(processing_state.get("inferred_project_ids")),
                "confidence": processing_state.get("project_confidence", 0.0),
                "inferred_project_ids": processing_state.get("inferred_project_ids", []),
                "final_project_ids": final_project_ids or [],
                "cleaned_query": processing_state["project_cleaned_query"] if processing_state["project_cleaned_query"] != processing_state["original_query"] else None,
                "metadata": processing_state.get("project_inference_metadata")
            },
            "document_type_inference": {
                "attempted": processing_state["document_type_inference_metadata"] is not None,
                "applied": bool(processing_state.get("inferred_document_type_ids")),
                "confidence": processing_state.get("document_type_confidence", 0.0),
                "inferred_document_type_ids": processing_state.get("inferred_document_type_ids", []),
                "final_document_type_ids": final_document_type_ids or [],
                "cleaned_query": processing_state.get("doc_type_cleaned_query") if processing_state.get("doc_type_cleaned_query") and processing_state.get("doc_type_cleaned_query") != processing_state.get("project_cleaned_query", processing_state["original_query"]) else None,
                "metadata": processing_state.get("document_type_inference_metadata")
            },
            "summary": {
                "inference_applied": len(processing_state["steps_applied"]) > 0,
                "project_inference_successful": bool(processing_state.get("inferred_project_ids")),
                "document_type_inference_successful": bool(processing_state.get("inferred_document_type_ids")),
                "query_modified": processing_state["final_query"] != processing_state["original_query"]
            }
        }
        
        return response


# Global pipeline instance
inference_pipeline = InferencePipeline()
