// API client — all backend calls go through this module

import type {
  HealthResponse,
  IngestResponse,
  IngestedFilesResponse,
  QueryRequest,
  QueryResponse,
  SourceReference,
  TextIngestRequest,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`);
  return handleResponse<HealthResponse>(res);
}

// ---------------------------------------------------------------------------
// Ingestion
// ---------------------------------------------------------------------------

export async function ingestText(request: TextIngestRequest): Promise<IngestResponse> {
  const res = await fetch(`${API_URL}/ingest/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handleResponse<IngestResponse>(res);
}

export async function ingestFile(
  file: File,
  onProgress?: (progress: number) => void
): Promise<IngestResponse> {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";

  const endpointMap: Record<string, string> = {
    pdf: "pdf",
    png: "image",
    jpg: "image",
    jpeg: "image",
    mp3: "audio",
    wav: "audio",
    mp4: "video",
    mov: "video",
    txt: "text",
  };

  const endpoint = endpointMap[ext];
  if (!endpoint) {
    throw new Error(`Unsupported file type: .${ext}`);
  }

  // For .txt files, read content and use the text endpoint
  if (ext === "txt") {
    const text = await file.text();
    return ingestText({ text, source_name: file.name });
  }

  const formData = new FormData();

  // Image endpoint uses 'files' (multiple), others use 'file'
  if (endpoint === "image") {
    formData.append("files", file);
  } else {
    formData.append("file", file);
  }

  // Use XMLHttpRequest for progress tracking
  return new Promise<IngestResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as IngestResponse);
        } catch {
          reject(new Error("Invalid response from server"));
        }
      } else {
        let detail = `HTTP ${xhr.status}`;
        try {
          const body = JSON.parse(xhr.responseText) as { detail?: string; message?: string };
          detail = body.detail ?? body.message ?? detail;
        } catch {
          // ignore
        }
        reject(new Error(detail));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    xhr.open("POST", `${API_URL}/ingest/${endpoint}`);
    xhr.send(formData);
  });
}

// ---------------------------------------------------------------------------
// Query (non-streaming)
// ---------------------------------------------------------------------------

export async function query(request: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${API_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  return handleResponse<QueryResponse>(res);
}

// ---------------------------------------------------------------------------
// Query (streaming SSE)
// ---------------------------------------------------------------------------

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onSources: (sources: SourceReference[]) => void;
  onDone: () => void;
  onError: (error: string) => void;
}

export async function queryStream(
  request: QueryRequest,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    callbacks.onError(detail);
    return;
  }

  if (!res.body) {
    callbacks.onError("No response body for streaming");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE lines
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? ""; // Keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;

        const data = trimmed.slice(5).trim();
        if (data === "[DONE]") {
          callbacks.onDone();
          return;
        }

        try {
          const parsed = JSON.parse(data) as Record<string, unknown>;

          if ("content" in parsed && typeof parsed.content === "string") {
            callbacks.onToken(parsed.content);
          } else if ("sources" in parsed && Array.isArray(parsed.sources)) {
            callbacks.onSources(parsed.sources as SourceReference[]);
          } else if ("error" in parsed && typeof parsed.error === "string") {
            callbacks.onError(parsed.error);
            return;
          }
        } catch {
          // Ignore malformed JSON lines
        }
      }
    }
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      // Intentional abort — do not call onError
      return;
    }
    callbacks.onError(err instanceof Error ? err.message : "Stream reading failed");
  } finally {
    reader.releaseLock();
  }
}

// ---------------------------------------------------------------------------
// Ingested files list
// ---------------------------------------------------------------------------

export async function getIngestedFiles(): Promise<IngestedFilesResponse> {
  const res = await fetch(`${API_URL}/ingested`);
  return handleResponse<IngestedFilesResponse>(res);
}

export async function deleteIngestedFile(
  source_type: string,
  source_file: string
): Promise<{ deleted: number }> {
  const params = new URLSearchParams({ source_type, source_file });
  const res = await fetch(`${API_URL}/ingested?${params}`, { method: "DELETE" });
  return handleResponse<{ deleted: number }>(res);
}
