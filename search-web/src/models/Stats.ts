// Stats API Response Models

export interface StatsMetrics {
  start_time: string;
  total_time_ms: number;
}

export interface SummaryStatsResponse {
  result: {
    processing_summary: {
      total_projects: number;
      total_files_across_all_projects: number;
      total_successful_files: number;
      total_failed_files: number;
      overall_success_rate: number;
      projects_with_failures: number;
      avg_success_rate_per_project: number;
    };
    metrics: StatsMetrics;
  };
}

export interface ProjectStats {
  project_id: string;
  project_name: string;
  total_files: number;
  successful_files: number;
  failed_files: number;
  success_rate: number;
}

export interface ProcessingStatsResponse {
  result: {
    processing_stats: {
      projects: ProjectStats[];
      summary: {
        total_projects: number;
        total_files_across_all_projects: number;
        total_successful_files: number;
        total_failed_files: number;
        overall_success_rate: number;
      };
    };
    metrics: StatsMetrics;
  };
}

export interface DocumentInfo {
  s3_key: string;
  metadata: {
    title: string;
    author: string;
    format: string;
    creator: string;
    modDate: string;
    subject: string;
    trapped: string;
    keywords: string;
    producer: string;
    encryption: string | null;
    creationDate: string;
  };
  page_count: number;
  pdf_version: string | null;
  display_name: string;
  document_name: string;
  file_size_bytes: number;
  validation_reason: string | null;
  validation_status: string;
}

export interface ProcessingMetrics {
  document_info: DocumentInfo;
  read_as_pages?: number;
  chunk_and_embed_pages?: {
    pages: number;
    avg_chunks_per_page: number;
    get_tags_time_total: number;
    embedding_time_total: number;
    get_keywords_time_total: number;
  };
  upsert_document_record?: number;
  download_and_validate_pdf: number;
  process_and_insert_chunks?: number;
  chunk_and_embed_pages_time?: number;
}

export interface ProcessingLog {
  log_id: number;
  document_id: string;
  status: "success" | "failure";
  processed_at: string;
  metrics: ProcessingMetrics | null;
}

export interface ProjectDetailsResponse {
  result: {
    project_details: {
      project_id: string;
      project_name: string;
      processing_logs: ProcessingLog[];
      summary: {
        total_files: number;
        successful_files: number;
        failed_files: number;
        success_rate: number;
      };
    };
    metrics: StatsMetrics;
  };
}
