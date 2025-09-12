"""Ollama summarizer implementation."""

import logging
from typing import List, Dict, Any, Optional
from flask import current_app
from .ollama_client import OllamaClient
from ...abstractions.summarizer import Summarizer

logger = logging.getLogger(__name__)


class OllamaSummarizer(Summarizer):
    """Ollama implementation of the summarizer."""
    
    def __init__(self):
        """Initialize the Ollama summarizer."""
        self.client = OllamaClient()
        
        # Load configuration with fallbacks
        self.temperature = getattr(current_app.config, 'LLM_TEMPERATURE', 0.3)
        self.max_tokens = getattr(current_app.config, 'LLM_MAX_TOKENS', 1000)
        self.max_context_length = getattr(current_app.config, 'LLM_MAX_CONTEXT_LENGTH', 8192)
    
    def summarize_search_results(
        self, 
        query: str, 
        documents_or_chunks: List[Dict[str, Any]],
        search_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Summarize search results using Ollama.
        
        Args:
            query: Original search query
            documents_or_chunks: List of document/chunk dictionaries
            search_context: Additional context about the search
            
        Returns:
            Dict containing summarization result
        """
        try:
            logger.info(f"Summarizing {len(documents_or_chunks)} documents/chunks using Ollama")
            
            # Use the existing summarize_documents method
            summary_text = self.summarize_documents(
                documents=documents_or_chunks,
                query=query,
                context=search_context.get('context') if search_context else None
            )
            
            return {
                'summary': summary_text,
                'method': 'ollama_summarization',
                'confidence': 0.8,  # Default confidence for Ollama
                'documents_count': len(documents_or_chunks),
                'provider': self.client.get_provider_name(),
                'model': self.client.get_model_name()
            }
            
        except Exception as e:
            logger.error(f"Ollama summarization failed: {str(e)}")
            return {
                'summary': f"Error generating summary: {str(e)}",
                'method': 'error_fallback',
                'confidence': 0.0,
                'documents_count': len(documents_or_chunks),
                'provider': 'ollama',
                'model': 'unknown'
            }
    
    def summarize_documents(
        self,
        documents: List[Dict[str, Any]],
        query: str,
        context: Optional[str] = None
    ) -> str:
        """Summarize a list of documents in relation to a query using Ollama.
        
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
            
            # Prepare document content (with more aggressive truncation for Ollama)
            doc_content = self._prepare_document_content(documents)
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Query: {query}\n\nDocuments to summarize:\n{doc_content}"}
            ]
            
            logger.info(f"Summarizing {len(documents)} documents using Ollama")
            response = self.client.chat_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=min(self.max_tokens, 1500)  # Use config value but cap for Ollama summarization
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
        """Create a formatted response based on the summary using Ollama.
        
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
            
            logger.info("Creating formatted response using Ollama")
            response = self.client.chat_completion(
                messages=messages,
                temperature=self.temperature,
                max_tokens=min(self.max_tokens, 1200)  # Use config value but cap for Ollama response formatting
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
        prompt = f"""You are an expert document analyst. Your task is to create a concise summary of the provided documents that directly addresses the user's query.

Key instructions:
1. Focus on information that directly relates to the query: "{query}"
2. Provide a short, focused summary in 1-2 paragraphs maximum
3. Include the most important findings and key details
4. Use clear, professional language
5. Avoid lengthy sections and detailed breakdowns
6. Keep the response brief and to the point

{f"Additional context: {context}" if context else ""}

Provide a concise summary that answers the query directly without extensive formatting or multiple sections."""
        
        return prompt
    
    def _build_response_prompt(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Build the response formatting prompt."""
        prompt = """You are a professional assistant helping users understand document information. 

Create a concise, focused response that:
1. Directly answers the user's question based on the summary
2. Uses clear, accessible language
3. Keeps the response to 1-2 short paragraphs maximum
4. Provides the most important information without extensive formatting
5. Avoids multiple sections, headers, or bullet points unless absolutely necessary
6. Gets straight to the point

Keep the response brief and informative."""
        
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
    
    def _prepare_document_content(
        self, 
        documents: List[Dict[str, Any]], 
        max_doc_length: int = None
    ) -> str:
        """Prepare document content for summarization with context-aware truncation for Ollama."""
        content_parts = []
        
        # Calculate reasonable limits based on context length
        # Reserve tokens for prompt, response, and overhead (~30% of context for Ollama)
        available_tokens = int(self.max_context_length * 0.7)
        
        # Use provided max_doc_length or calculate based on context
        if max_doc_length is None:
            max_doc_length = min(2000, available_tokens // max(len(documents), 1))
        
        for i, doc in enumerate(documents, 1):
            title = doc.get("title", f"Document {i}")
            content = doc.get("content", "")
            doc_type = doc.get("document_type", "Unknown")
            
            # Truncate content based on calculated limits
            if len(content) > max_doc_length:
                content = content[:max_doc_length] + "..."
            
            content_parts.append(f"Document {i}: {title} (Type: {doc_type})\n{content}\n")
        
        # Also limit total content length to avoid context overflow
        full_content = "\n".join(content_parts)
        
        if len(full_content) > available_tokens:
            # Truncate and add note
            full_content = full_content[:available_tokens] + "\n\n[Content truncated due to context length limits...]"
        
        return full_content
    
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