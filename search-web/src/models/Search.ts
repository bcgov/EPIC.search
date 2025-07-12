export interface Document {
  document_id: string;
  document_type: string | null;
  document_name: string;
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
  const result = response.result;
  return result.documents || result.document_chunks || [];
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
