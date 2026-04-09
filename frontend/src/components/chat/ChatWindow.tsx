"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage, SourceType } from "@/lib/types";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSend: (message: string, sourceType?: SourceType | null) => void;
  onStop: () => void;
  onClear: () => void;
  error: string | null;
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <div className="w-16 h-16 bg-gray-800 rounded-2xl flex items-center justify-center mb-4">
        <svg
          className="w-8 h-8 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </div>
      <h3 className="text-gray-300 font-semibold text-lg mb-2">Start a conversation</h3>
      <p className="text-gray-500 text-sm max-w-sm leading-relaxed">
        Ask questions about your ingested documents. Make sure you&apos;ve uploaded some content in
        the{" "}
        <a href="/ingest" className="text-blue-400 hover:underline">
          Ingest Data
        </a>{" "}
        section first.
      </p>
      <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-sm">
        {[
          "Summarize the main points from the uploaded documents",
          "What are the key findings in the PDF?",
          "Describe what you see in the uploaded images",
        ].map((suggestion) => (
          <button
            key={suggestion}
            className="text-left px-4 py-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg text-gray-400 hover:text-gray-200 text-sm transition-colors"
            onClick={() => {
              // Clicking a suggestion would require wiring this up — handled by parent
            }}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatWindow({
  messages,
  isLoading,
  onSend,
  onStop,
  onClear,
  error,
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Toolbar */}
      {messages.length > 0 && (
        <div className="flex items-center justify-end px-4 py-2 border-b border-gray-700 flex-shrink-0">
          <button
            onClick={onClear}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-200 text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
            aria-label="Clear conversation"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear chat
          </button>
        </div>
      )}

      {/* Messages area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 py-6 space-y-6 min-h-0"
        role="log"
        aria-label="Chat messages"
        aria-live="polite"
      >
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
        )}

        {/* Global error banner */}
        {error && messages.length === 0 && (
          <div className="flex items-center gap-2 bg-red-900/30 border border-red-700 rounded-lg px-4 py-3 text-red-300 text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <ChatInput
        onSend={onSend}
        onStop={onStop}
        isLoading={isLoading}
      />
    </div>
  );
}
