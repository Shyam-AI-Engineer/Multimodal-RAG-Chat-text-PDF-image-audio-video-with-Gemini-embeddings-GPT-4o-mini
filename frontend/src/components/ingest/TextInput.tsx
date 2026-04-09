"use client";

import { useCallback, useState } from "react";

interface TextInputProps {
  onSubmit: (text: string, sourceName: string) => Promise<void>;
  disabled?: boolean;
  error?: string | null;
}

export function TextInput({ onSubmit, disabled = false, error }: TextInputProps) {
  const [text, setText] = useState("");
  const [sourceName, setSourceName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!text.trim() || isSubmitting || disabled) return;

      setIsSubmitting(true);
      setSuccess(false);

      try {
        await onSubmit(text.trim(), sourceName.trim() || "manual_input");
        setSuccess(true);
        setText("");
        setSourceName("");
        setTimeout(() => setSuccess(false), 3000);
      } catch {
        // Error is handled by the parent
      } finally {
        setIsSubmitting(false);
      }
    },
    [text, sourceName, isSubmitting, disabled, onSubmit]
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label htmlFor="source-name" className="block text-gray-400 text-sm mb-1.5">
          Source name <span className="text-gray-600">(optional)</span>
        </label>
        <input
          id="source-name"
          type="text"
          value={sourceName}
          onChange={(e) => setSourceName(e.target.value)}
          placeholder="e.g. company-policy, meeting-notes"
          disabled={disabled || isSubmitting}
          className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-200 placeholder-gray-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          suppressHydrationWarning
        />
      </div>

      <div>
        <label htmlFor="text-content" className="block text-gray-400 text-sm mb-1.5">
          Text content
        </label>
        <textarea
          id="text-content"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste your text here..."
          rows={8}
          disabled={disabled || isSubmitting}
          className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-gray-200 placeholder-gray-500 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 resize-y disabled:opacity-50"
          aria-describedby={error ? "text-error" : undefined}
          suppressHydrationWarning
        />
        <p className="text-gray-600 text-xs mt-1">{text.length.toLocaleString()} characters</p>
      </div>

      {error && (
        <div id="text-error" className="flex items-center gap-2 text-red-400 text-sm" role="alert">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </div>
      )}

      {success && (
        <div className="flex items-center gap-2 text-green-400 text-sm" role="status">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Text ingested successfully!
        </div>
      )}

      <button
        type="submit"
        disabled={!text.trim() || isSubmitting || disabled}
        className={`w-full py-2.5 rounded-lg text-sm font-medium transition-colors ${
          !text.trim() || isSubmitting || disabled
            ? "bg-gray-700 text-gray-500 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700 text-white"
        }`}
        aria-busy={isSubmitting}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Ingesting...
          </span>
        ) : (
          "Ingest Text"
        )}
      </button>
    </form>
  );
}
