export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed';
export type DocumentType = 'pdf' | 'docx' | 'txt' | 'md';

export interface Document {
  id: string;
  name: string;
  file_type: DocumentType;
  file_size: number;
  status: DocumentStatus;
  chunk_count: number;
  page_count: number | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  error_message: string | null;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  status: DocumentStatus;
  message: string;
  chunk_count: number;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number | null;
  text_excerpt: string;
  relevance_score: number;
  chunk_index: number;
}

export interface EvaluationMetrics {
  faithfulness: number;
  answer_relevancy: number;
  context_recall: number;
  context_precision: number;
}

export interface QueryRequest {
  query: string;
  top_k?: number;
  hybrid_alpha?: number;
  use_graph?: boolean;
  stream?: boolean;
  filters?: Record<string, unknown>;
}

export interface QueryResponse {
  query_id: string;
  query: string;
  answer: string;
  citations: Citation[];
  metrics: EvaluationMetrics;
  model_used: string;
  latency_ms: number;
  created_at: string;
  graph_entities: string[];
}

export type StreamChunkType = 'start' | 'token' | 'done' | 'error';

export interface StreamChunk {
  type: StreamChunkType;
  content: string;
  query_id?: string;
  citations?: Citation[];
  metrics?: EvaluationMetrics;
}

export interface DailyCount {
  date: string;
  count: number;
}

export interface UsageStats {
  total_queries: number;
  queries_today: number;
  total_documents: number;
  total_chunks: number;
  avg_latency_ms: number;
  queries_per_day: DailyCount[];
}

export interface DailyMetrics {
  date: string;
  faithfulness: number;
  answer_relevancy: number;
  context_recall: number;
}

export interface QualityMetrics {
  avg_faithfulness: number;
  avg_answer_relevancy: number;
  avg_context_recall: number;
  avg_context_precision: number;
  metrics_over_time: DailyMetrics[];
  sample_size: number;
}

export type MessageRole = 'user' | 'assistant';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  metrics?: EvaluationMetrics;
  latency_ms?: number;
  graph_entities?: string[];
  timestamp: Date;
  isStreaming?: boolean;
}
