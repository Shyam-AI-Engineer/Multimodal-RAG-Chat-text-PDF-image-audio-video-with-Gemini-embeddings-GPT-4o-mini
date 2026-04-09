"use client";

import type { UploadItem, UploadStatus } from "@/lib/types";

interface IngestionStatusProps {
  item: UploadItem;
  onRemove: (id: string) => void;
}

const STATUS_CONFIG: Record<UploadStatus, { color: string; label: string; icon: React.ReactNode }> = {
  idle: {
    color: "text-gray-400 border-gray-600",
    label: "Queued",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  uploading: {
    color: "text-blue-400 border-blue-700",
    label: "Uploading",
    icon: (
      <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
  },
  processing: {
    color: "text-yellow-400 border-yellow-700",
    label: "Processing",
    icon: (
      <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      </svg>
    ),
  },
  success: {
    color: "text-green-400 border-green-700",
    label: "Success",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    ),
  },
  error: {
    color: "text-red-400 border-red-700",
    label: "Error",
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
    ),
  },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function IngestionStatus({ item, onRemove }: IngestionStatusProps) {
  const config = STATUS_CONFIG[item.status];
  const isActive = item.status === "uploading" || item.status === "processing";

  return (
    <div
      className={`flex items-start gap-3 p-3 bg-gray-800 border rounded-lg ${config.color}`}
      role="status"
      aria-label={`${item.file.name}: ${config.label}`}
    >
      <div className={`flex-shrink-0 mt-0.5 ${config.color.split(" ")[0]}`}>
        {config.icon}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-gray-200 text-sm font-medium truncate" title={item.file.name}>
            {item.file.name}
          </p>
          {!isActive && (
            <button
              onClick={() => onRemove(item.id)}
              className="flex-shrink-0 text-gray-500 hover:text-gray-300 transition-colors"
              aria-label={`Remove ${item.file.name}`}
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        <p className="text-gray-500 text-xs mt-0.5">
          {formatFileSize(item.file.size)} · {item.file.type || "unknown type"}
        </p>

        {/* Progress bar */}
        {item.status === "uploading" && (
          <div className="mt-2">
            <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${item.progress}%` }}
                aria-valuenow={item.progress}
                aria-valuemin={0}
                aria-valuemax={100}
                role="progressbar"
              />
            </div>
          </div>
        )}

        {item.message && (
          <p className={`text-xs mt-1.5 ${item.status === "error" ? "text-red-400" : "text-gray-400"}`}>
            {item.message}
          </p>
        )}
      </div>
    </div>
  );
}
