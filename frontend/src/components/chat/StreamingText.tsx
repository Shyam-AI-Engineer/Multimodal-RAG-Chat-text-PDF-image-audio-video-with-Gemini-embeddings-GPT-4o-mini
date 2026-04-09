"use client";

interface StreamingTextProps {
  content: string;
  isStreaming: boolean;
}

export function StreamingText({ content, isStreaming }: StreamingTextProps) {
  return (
    <div className="prose prose-invert prose-sm max-w-none">
      <span className="whitespace-pre-wrap break-words text-gray-100 leading-relaxed">
        {content}
      </span>
      {isStreaming && (
        <span
          className="inline-block w-0.5 h-4 bg-blue-400 ml-0.5 animate-pulse align-middle"
          aria-hidden="true"
        />
      )}
    </div>
  );
}
