export interface Document {
  document_id: string;
  document_type: string | null;
  document_name: string;
  document_display_name: string;
  document_saved_name: string;
  page_number: string | null;
  project_id: string;
  project_name: string;
  proponent_name?: string;
  content: string;
  s3_key?: string;
  document_date?: string;
  relevance_score?: number;
  search_mode?: string;
}

export interface SearchResult {
  response: string;
  documents?: Document[];
  document_chunks?: Document[];
}

export interface SearchResponse {
  result: SearchResult;
}

// Helper function to extract documents from either documents or document_chunks
export function getDocumentsFromResponse(response: SearchResponse): Document[] {
  try {
    // Safety checks
    if (!response || !response.result) {
      console.warn('Invalid search response structure');
      return [];
    }
    
    const result = response.result;
    const allDocuments: Document[] = [];
    
    // Add documents if they exist and are an array
    if (Array.isArray(result.documents)) {
      allDocuments.push(...result.documents);
    }
    
    // Add document_chunks if they exist and are an array
    if (Array.isArray(result.document_chunks)) {
      allDocuments.push(...result.document_chunks);
    }
    
    if (allDocuments.length === 0) {
      console.warn('No valid documents or document_chunks found in response');
    }
    
    return allDocuments;
  } catch (error) {
    console.error('Error extracting documents from response:', error);
    return [];
  }
}

export interface SimilarSearchRequest {
  documentId: string;
  projectIds?: string[];
  limit: number;
}

export interface SimilarSearchResponse {
  result: {
    documents: Document[];
  };
}
