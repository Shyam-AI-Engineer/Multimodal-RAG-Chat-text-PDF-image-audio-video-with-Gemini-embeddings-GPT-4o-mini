"use client";

import { useCallback, useRef, useState } from "react";
import type { SourceType } from "@/lib/types";

interface ChatInputProps {
  onSend: (message: string, sourceType?: SourceType | null) => void;
  onStop: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

const SOURCE_TYPE_OPTIONS: Array<{ value: SourceType | "all"; label: string }> = [
  { value: "all", label: "All sources" },
  { value: "text", label: "Text" },
  { value: "pdf", label: "PDF" },
  { value: "image", label: "Image" },
  { value: "audio", label: "Audio" },
  { value: "video", label: "Video" },
];

export function ChatInput({ onSend, onStop, isLoading, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceType | "all">("all");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = message.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed, sourceFilter === "all" ? null : sourceFilter);
    setMessage("");
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [message, sourceFilter, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Auto-resize textarea
    const ta = e.target;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 200)}px`;
  }, []);

  const canSend = message.trim().length > 0 && !isLoading && !disabled;

  return (
    <div className="border-t border-gray-700 bg-gray-900 px-4 py-4">
      {/* Source filter */}
      <div className="flex items-center gap-2 mb-3">
        <label htmlFor="source-filter" className="text-gray-400 text-xs flex-shrink-0">
          Filter:
        </label>
        <select
          id="source-filter"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value as SourceType | "all")}
          className="bg-gray-800 border border-gray-600 text-gray-300 text-xs rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          disabled={isLoading}
          aria-label="Filter results by source type"
        >
          {SOURCE_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Input area */}
      <div className="flex items-end gap-3 bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 focus-within:border-blue-500 transition-colors">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents... (Enter to send, Shift+Enter for newline)"
          rows={1}
          disabled={disabled}
          aria-label="Chat message input"
          className="flex-1 bg-transparent text-gray-100 placeholder-gray-500 text-sm resize-none focus:outline-none leading-relaxed"
          style={{ maxHeight: "200px", minHeight: "24px" }}
          suppressHydrationWarning
        />

        {isLoading ? (
          <button
            type="button"
            onClick={onStop}
            className="flex-shrink-0 w-8 h-8 bg-red-600 hover:bg-red-700 rounded-lg flex items-center justify-center transition-colors"
            aria-label="Stop generating"
          >
            <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
              <rect x="2" y="2" width="8" height="8" rx="1" />
            </svg>
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSend}
            disabled={!canSend}
            className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
              canSend
                ? "bg-blue-600 hover:bg-blue-700 text-white"
                : "bg-gray-700 text-gray-500 cursor-not-allowed"
            }`}
            aria-label="Send message"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        )}
      </div>

      <p className="text-gray-600 text-xs mt-2 text-center">
        Answers are based on your ingested documents only
      </p>
    </div>
  );
}
