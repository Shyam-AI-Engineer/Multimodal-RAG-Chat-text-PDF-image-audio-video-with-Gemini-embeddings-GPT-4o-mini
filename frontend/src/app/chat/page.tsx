"use client";

import { ChatWindow } from "@/components/chat/ChatWindow";
import { Header } from "@/components/layout/Header";
import { useChat } from "@/hooks/useChat";

export default function ChatPage() {
  const { messages, isLoading, sendMessage, stopStreaming, clearMessages, error } = useChat();

  return (
    <div className="flex flex-col h-full min-h-0">
      <Header
        title="Chat"
        subtitle="Ask questions about your ingested documents"
        actions={
          isLoading ? (
            <span className="text-blue-400 text-xs flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
              Generating...
            </span>
          ) : undefined
        }
      />
      <div className="flex-1 min-h-0">
        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSend={sendMessage}
          onStop={stopStreaming}
          onClear={clearMessages}
          error={error}
        />
      </div>
    </div>
  );
}
