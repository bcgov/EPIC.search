"""OpenAI summarizer implementation."""

import logging
from typing import List, Dict, Any, Optional
from .openai_client import OpenAIClient
from ...abstractions.summarizer import Summarizer

logger = logging.getLogger(__name__)


class OpenAISummarizer(Summarizer):
    """OpenAI implementation of the summarizer."""
    
    def __init__(self):
        """Initialize the OpenAI summarizer."""
        self.client = OpenAIClient()
    
    def summarize_search_results(
        self, 
        query: str, 
        documents_or_chunks: List[Dict[str, Any]],
        search_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Summarize search results using OpenAI.
        
        Args:
            query: Original search query
            documents_or_chunks: List of document/chunk dictionaries
            search_context: Additional context about the search
            
        Returns:
            Dict containing summarization result
        """
        try:
            logger.info(f"Summarizing {len(documents_or_chunks)} documents/chunks using OpenAI")
            
            # Use the existing summarize_documents method
            summary_text = self.summarize_documents(
                documents=documents_or_chunks,
                query=query,
                context=search_context.get('context') if search_context else None
            )
            
            return {
                'summary': summary_text,
                'method': 'openai_summarization',
                'confidence': 0.8,  # Default confidence for OpenAI
                'documents_count': len(documents_or_chunks),
                'provider': self.client.get_provider_name(),
                'model': self.client.get_model_name()
            }
            
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {str(e)}")
            return {
                'summary': f"Error generating summary: {str(e)}",
                'method': 'error_fallback',
                'confidence': 0.0,
                'documents_count': len(documents_or_chunks),
                'provider': 'openai',
                'model': 'unknown'
            }
    
    def summarize_documents(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        context: Optional[str] = None
    ) -> str:
        """Summarize a list of documents in relation to a query using OpenAI.
        
        Args:
            documents: List of document dictionaries with content and metadata.
            query: The original search query for context.
            context: Optional additional context for summarization.
            
        Returns:
            str: A comprehensive summary of the documents.
            
        Raises:
            Exception: If summarization fails.
        """
        try:
            if not documents:
                return "No documents found to summarize."
            
            # Build the summarization prompt
            prompt = self._build_summarization_prompt(query, context)
            
            # Prepare document content
            doc_content = self._prepare_document_content(documents)
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocuments to summarize:\n{doc_content}"}
            ]
            
            logger.info(f"Summarizing {len(documents)} documents using OpenAI")
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            summary = response["choices"][0]["message"]["content"]
            logger.info("Document summarization completed successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Document summarization failed: {str(e)}")
            # Return a basic fallback summary
            return self._fallback_summary(documents, query)
    
    def create_response(
        self,
        summary: str,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a formatted response based on the summary using OpenAI.
        
        Args:
            summary: The document summary.
            query: The original search query.
            metadata: Optional metadata about the search.
            
        Returns:
            str: A well-formatted response.
            
        Raises:
            Exception: If response creation fails.
        """
        try:
            # Build the response formatting prompt
            prompt = self._build_response_prompt(metadata)
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Query: {query}\n\nSummary: {summary}\n\nCreate a comprehensive response."}
            ]
            
            logger.info("Creating formatted response using OpenAI")
            response = self.client.chat_completion(
                messages=messages,
                temperature=0.5,
                max_tokens=1500
            )
            
            formatted_response = response["choices"][0]["message"]["content"]
            logger.info("Response formatting completed successfully")
            return formatted_response
            
        except Exception as e:
            logger.error(f"Response creation failed: {str(e)}")
            # Return the summary as fallback
            return f"Based on the available documents, here's what I found:\n\n{summary}"
    
    def _build_summarization_prompt(self, query: str, context: Optional[str] = None) -> str:
        """Build the summarization prompt."""
        prompt = f"""You are an expert document analyst. Your task is to create a comprehensive summary of the provided documents that directly addresses the user's query.

Key instructions:
1. Focus on information that directly relates to the query: "{query}"
2. Organize information logically with clear sections and headings
3. Include specific details, numbers, dates, and technical specifications when relevant
4. Highlight important findings, conclusions, and recommendations
5. Note any conflicting information or gaps in the data
6. Use clear, professional language appropriate for technical documentation
7. Cite document titles or sources when referencing specific information

Structure your summary with:
- Executive Summary (key findings)
- Detailed Analysis (organized by topic/theme)
- Important Details (specific data, dates, requirements)
- Conclusions and Recommendations (if applicable)

{f"Additional context: {context}" if context else ""}

Make the summary comprehensive but focused on the query's intent."""
        
        return prompt
    
    def _build_response_prompt(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Build the response formatting prompt."""
        prompt = """You are a professional assistant helping users understand complex document information. 

Create a well-structured, comprehensive response that:
1. Directly answers the user's question based on the summary
2. Uses clear, accessible language while maintaining technical accuracy
3. Organizes information with appropriate headings and bullet points
4. Provides specific details and examples when available
5. Acknowledges limitations or gaps in the information
6. Offers actionable insights or next steps when appropriate

Format the response professionally with proper headings, bullet points, and clear organization."""
        
        if metadata:
            search_info = []
            if metadata.get("document_count"):
                search_info.append(f"searched {metadata['document_count']} documents")
            if metadata.get("project_ids"):
                search_info.append(f"across projects: {', '.join(metadata['project_ids'])}")
            if metadata.get("document_types"):
                search_info.append(f"document types: {', '.join(metadata['document_types'])}")
            
            if search_info:
                prompt += f"\n\nContext: This response is based on information from {', '.join(search_info)}."
        
        return prompt
    
    def _prepare_document_content(self, documents: List[Dict[str, Any]]) -> str:
        """Prepare document content for summarization."""
        content_parts = []
        
        for i, doc in enumerate(documents, 1):
            title = doc.get("title", f"Document {i}")
            content = doc.get("content", "")
            doc_type = doc.get("document_type", "Unknown")
            
            # Truncate very long content to avoid token limits
            if len(content) > 3000:
                content = content[:3000] + "..."
            
            content_parts.append(f"Document {i}: {title} (Type: {doc_type})\n{content}\n")
        
        return "\n".join(content_parts)
    
    def _fallback_summary(self, documents: List[Dict[str, Any]], query: str) -> str:
        """Provide a basic fallback summary when LLM fails."""
        doc_count = len(documents)
        doc_types = list(set(doc.get("document_type", "Unknown") for doc in documents))
        
        summary = f"Found {doc_count} relevant documents related to '{query}'.\n\n"
        summary += f"Document types included: {', '.join(doc_types)}\n\n"
        
        # Include first few document titles
        for i, doc in enumerate(documents[:3], 1):
            title = doc.get("title", f"Document {i}")
            summary += f"- {title}\n"
        
        if len(documents) > 3:
            summary += f"... and {len(documents) - 3} more documents.\n"
        
        summary += "\nPlease review the individual documents for detailed information."
        
        return summary