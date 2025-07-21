"""Inference pipeline package for search query processing.

This package contains intelligent inference services that automatically detect
and extract context from natural language search queries. The inference pipeline
processes queries sequentially to identify:

1. Project references - Automatic project ID inference from project names
2. Document type references - Automatic document type ID inference from type names
3. Future extensions - Additional context extraction capabilities

The pipeline is designed to be extensible and maintains transparency through
detailed metadata reporting of each inference step.

Example usage:
    from src.services.inference import InferencePipeline
    
    pipeline = InferencePipeline()
    result = pipeline.process_query(
        query="I am looking for correspondence about Indigenous nations for the Coyote Hydrogen project",
        project_ids=None,  # Will trigger project inference
        document_type_ids=None  # Will trigger document type inference
    )
"""

from .inference_pipeline import InferencePipeline
from .project_inference import project_inference_service
from .document_type_inference import DocumentTypeInferenceService

# Create singleton instance
document_type_inference_service = DocumentTypeInferenceService()

__all__ = [
    'InferencePipeline',
    'project_inference_service',
    'document_type_inference_service'
]
