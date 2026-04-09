"use client";

import type { ChatMessage } from "@/lib/types";
import { SourceCard } from "./SourceCard";
import { StreamingText } from "./StreamingText";

interface MessageBubbleProps {
  message: ChatMessage;
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1" aria-label="Assistant is typing">
      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div
      className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 text-white text-sm font-semibold"
      aria-hidden="true"
    >
      U
    </div>
  );
}

function AssistantAvatar() {
  return (
    <div
      className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0 text-white text-sm font-semibold"
      aria-hidden="true"
    >
      AI
    </div>
  );
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming ?? false;
  const showTypingIndicator = isStreaming && !message.content;

  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end" role="article" aria-label="Your message">
        <div className="flex flex-col items-end max-w-[80%]">
          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5">
            <p className="text-sm whitespace-pre-wrap break-words leading-relaxed">
              {message.content}
            </p>
          </div>
          <span className="text-gray-500 text-xs mt-1 px-1">
            {`${String(message.timestamp.getHours()).padStart(2,"0")}:${String(message.timestamp.getMinutes()).padStart(2,"0")}`}
          </span>
        </div>
        <UserAvatar />
      </div>
    );
  }

  // Assistant message
  return (
    <div className="flex items-start gap-3" role="article" aria-label="Assistant message">
      <AssistantAvatar />
      <div className="flex flex-col max-w-[85%] min-w-0">
        <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-2.5">
          {showTypingIndicator ? (
            <TypingIndicator />
          ) : (
            <StreamingText content={message.content} isStreaming={isStreaming} />
          )}
          {message.error && !message.content && (
            <p className="text-red-400 text-sm">{message.error}</p>
          )}
        </div>

        {/* Sources section */}
        {message.sources && message.sources.length > 0 && !isStreaming && (
          <div className="mt-3">
            <p className="text-gray-500 text-xs mb-2 px-1">
              {message.sources.length} source{message.sources.length > 1 ? "s" : ""} retrieved
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {message.sources.map((source, idx) => (
                <SourceCard key={`${source.source_file}-${source.chunk_index}`} source={source} index={idx} />
              ))}
            </div>
          </div>
        )}

        <span className="text-gray-500 text-xs mt-1 px-1">
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </div>
  );
}
