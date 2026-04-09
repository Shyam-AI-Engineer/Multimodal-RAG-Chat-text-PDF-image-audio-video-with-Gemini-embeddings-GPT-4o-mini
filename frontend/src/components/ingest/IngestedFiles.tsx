"use client";

import { useCallback, useState } from "react";
import { deleteIngestedFile } from "@/lib/api";
import type { IngestedFileRecord, SourceType } from "@/lib/types";

interface IngestedFilesProps {
  files: IngestedFileRecord[];
  isLoading: boolean;
  onRefresh: () => void;
}

const SOURCE_TYPE_BADGES: Record<SourceType, string> = {
  text: "bg-blue-900/50 text-blue-300 border-blue-700",
  pdf: "bg-red-900/50 text-red-300 border-red-700",
  image: "bg-purple-900/50 text-purple-300 border-purple-700",
  audio: "bg-green-900/50 text-green-300 border-green-700",
  video: "bg-orange-900/50 text-orange-300 border-orange-700",
};

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    const h = String(d.getHours()).padStart(2, "0");
    const m = String(d.getMinutes()).padStart(2, "0");
    return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} ${h}:${m}`;
  } catch {
    return ts;
  }
}

export function IngestedFiles({ files, isLoading, onRefresh }: IngestedFilesProps) {
  const [deletingKey, setDeletingKey] = useState<string | null>(null);

  const handleDelete = useCallback(async (file: IngestedFileRecord) => {
    const key = `${file.source_type}::${file.source_file}`;
    setDeletingKey(key);
    try {
      await deleteIngestedFile(file.source_type, file.source_file);
      await onRefresh();
    } catch {
      // silently ignore
    } finally {
      setDeletingKey(null);
    }
  }, [onRefresh]);

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-gray-300 font-medium text-sm">
          Ingested Files
          {files.length > 0 && (
            <span className="ml-2 text-gray-500">({files.length})</span>
          )}
        </h3>
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="text-gray-400 hover:text-gray-200 text-xs flex items-center gap-1 transition-colors disabled:opacity-50"
          aria-label="Refresh ingested files list"
        >
          <svg
            className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {isLoading && files.length === 0 ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-14 bg-gray-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : files.length === 0 ? (
        <div className="text-center py-8 bg-gray-800/50 border border-gray-700 rounded-lg">
          <svg
            className="w-8 h-8 text-gray-600 mx-auto mb-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-gray-500 text-sm">No files ingested yet</p>
        </div>
      ) : (
        <ul className="space-y-2" aria-label="List of ingested files">
          {files.map((file, idx) => {
            const badgeClass = SOURCE_TYPE_BADGES[file.source_type] ?? SOURCE_TYPE_BADGES.text;
            return (
              <li
                key={`${file.source_type}-${file.source_file}-${idx}`}
                className="flex items-center gap-3 p-3 bg-gray-800 border border-gray-700 rounded-lg"
              >
                <span
                  className={`text-xs px-2 py-0.5 rounded border font-medium flex-shrink-0 ${badgeClass}`}
                >
                  {file.source_type}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-gray-200 text-sm truncate" title={file.source_file}>
                    {file.source_file}
                  </p>
                  <p className="text-gray-500 text-xs mt-0.5" suppressHydrationWarning>
                    {file.chunk_count} chunk{file.chunk_count !== 1 ? "s" : ""} ·{" "}
                    {file.timestamp ? formatTimestamp(file.timestamp) : "Unknown date"}
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(file)}
                  disabled={deletingKey === `${file.source_type}::${file.source_file}`}
                  className="flex-shrink-0 text-gray-600 hover:text-red-400 transition-colors disabled:opacity-40"
                  aria-label={`Delete ${file.source_file}`}
                  title="Delete"
                >
                  {deletingKey === `${file.source_type}::${file.source_file}` ? (
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
