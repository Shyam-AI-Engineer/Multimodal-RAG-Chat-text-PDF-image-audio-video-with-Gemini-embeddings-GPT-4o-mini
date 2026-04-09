"use client";

import { useCallback, useRef, useState } from "react";
import { queryStream } from "@/lib/api";
import type { ChatMessage, SourceReference, SourceType } from "@/lib/types";

function generateId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  sendMessage: (question: string, sourceType?: SourceType | null) => Promise<void>;
  stopStreaming: () => void;
  clearMessages: () => void;
  error: string | null;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const sendMessage = useCallback(
    async (question: string, sourceType?: SourceType | null) => {
      if (!question.trim() || isLoading) return;

      setError(null);

      // Add user message
      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      // Add placeholder assistant message
      const assistantId = generateId();
      const assistantMessage: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        sources: [],
        isStreaming: true,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      abortControllerRef.current = new AbortController();

      try {
        await queryStream(
          {
            question: question.trim(),
            source_type: sourceType ?? null,
            top_k: 5,
          },
          {
            onToken: (token) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: msg.content + token }
                    : msg
                )
              );
            },
            onSources: (sources: SourceReference[]) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId ? { ...msg, sources } : msg
                )
              );
            },
            onDone: () => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId ? { ...msg, isStreaming: false } : msg
                )
              );
              setIsLoading(false);
              abortControllerRef.current = null;
            },
            onError: (errMsg) => {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        content: msg.content || "An error occurred while generating the response.",
                        isStreaming: false,
                        error: errMsg,
                      }
                    : msg
                )
              );
              setError(errMsg);
              setIsLoading(false);
              abortControllerRef.current = null;
            },
          },
          abortControllerRef.current.signal
        );
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : "Unknown error occurred";
        if (errMsg !== "AbortError") {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    content: "Failed to connect to the server. Please try again.",
                    isStreaming: false,
                    error: errMsg,
                  }
                : msg
            )
          );
          setError(errMsg);
        }
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [isLoading]
  );

  return { messages, isLoading, sendMessage, stopStreaming, clearMessages, error };
}
