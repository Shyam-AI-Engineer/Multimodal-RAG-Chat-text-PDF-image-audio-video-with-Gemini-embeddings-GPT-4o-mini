// TypeScript interfaces for all API payloads and UI state

export type SourceType = "text" | "pdf" | "image" | "audio" | "video";

// ---------------------------------------------------------------------------
// Source reference from Pinecone
// ---------------------------------------------------------------------------
export interface SourceReference {
  source_type: SourceType;
  source_file: string;
  chunk_index: number;
  content_preview: string;
  score: number;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------
export interface TextIngestRequest {
  text: string;
  source_name?: string;
}

export interface IngestResponse {
  status: "success" | "error";
  message: string;
  source_type: SourceType;
  source_file: string;
  chunks_stored: number;
  timestamp: string;
}

export interface IngestedFileRecord {
  source_type: SourceType;
  source_file: string;
  chunk_count: number;
  timestamp: string;
}

export interface IngestedFilesResponse {
  files: IngestedFileRecord[];
  total: number;
}

// ---------------------------------------------------------------------------
// Query
// ---------------------------------------------------------------------------
export interface QueryRequest {
  question: string;
  source_type?: SourceType | null;
  top_k?: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceReference[];
  question: string;
}

// ---------------------------------------------------------------------------
// Chat UI state
// ---------------------------------------------------------------------------
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceReference[];
  isStreaming?: boolean;
  timestamp: Date;
  error?: string;
}

// ---------------------------------------------------------------------------
// Ingestion UI state
// ---------------------------------------------------------------------------
export type UploadStatus = "idle" | "uploading" | "processing" | "success" | "error";

export interface UploadItem {
  id: string;
  file: File;
  status: UploadStatus;
  progress: number;
  message: string;
  response?: IngestResponse;
  error?: string;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export interface HealthResponse {
  status: string;
  service: string;
}

// ---------------------------------------------------------------------------
// SSE streaming events
// ---------------------------------------------------------------------------
export interface SSEContentEvent {
  content: string;
}

export interface SSESourcesEvent {
  sources: SourceReference[];
}

export interface SSEErrorEvent {
  error: string;
}

export type SSEEvent = SSEContentEvent | SSESourcesEvent | SSEErrorEvent;
