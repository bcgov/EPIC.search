
export interface Document {
  document_id: string;
  document_type: string | null;
  document_name: string;
  document_saved_name: string;
  page_number: string;
  project_id: string;
  project_name: string;
  content: string;
  s3_key: string;
}

export interface SearchResponse {
  result: {
    documents: Document[];
    response: string;
  };
}
