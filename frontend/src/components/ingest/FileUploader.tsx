"use client";

import { useCallback, useRef, useState } from "react";

interface FileUploaderProps {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const ACCEPTED_EXTENSIONS = [".txt", ".pdf", ".png", ".jpg", ".jpeg", ".mp3", ".wav", ".mp4", ".mov"];
const ACCEPT_STRING = ACCEPTED_EXTENSIONS.join(",");

const FILE_TYPE_INFO = [
  { label: "Text", exts: ".txt", color: "text-blue-400" },
  { label: "PDF", exts: ".pdf", color: "text-red-400" },
  { label: "Images", exts: ".png, .jpg", color: "text-purple-400" },
  { label: "Audio", exts: ".mp3, .wav", color: "text-green-400" },
  { label: "Video", exts: ".mp4, .mov", color: "text-orange-400" },
];

export function FileUploader({ onFiles, disabled = false }: FileUploaderProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || disabled) return;
      const validFiles = Array.from(files).filter((file) => {
        const ext = "." + (file.name.split(".").pop()?.toLowerCase() ?? "");
        return ACCEPTED_EXTENSIONS.includes(ext);
      });
      if (validFiles.length > 0) {
        onFiles(validFiles);
      }
    },
    [onFiles, disabled]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleClick = useCallback(() => {
    if (!disabled) fileInputRef.current?.click();
  }, [disabled]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleClick();
      }
    },
    [handleClick]
  );

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload files — drag and drop or click to browse"
        aria-disabled={disabled}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 ${
          disabled
            ? "opacity-50 cursor-not-allowed border-gray-700"
            : isDragOver
            ? "border-blue-500 bg-blue-900/20"
            : "border-gray-600 hover:border-gray-500 hover:bg-gray-800/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPT_STRING}
          onChange={(e) => handleFiles(e.target.files)}
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          disabled={disabled}
        />

        <div className="flex flex-col items-center gap-3">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
            isDragOver ? "bg-blue-600" : "bg-gray-700"
          }`}>
            <svg
              className="w-6 h-6 text-gray-300"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>

          <div>
            <p className="text-gray-200 font-medium">
              {isDragOver ? "Drop files here" : "Drag & drop files"}
            </p>
            <p className="text-gray-400 text-sm mt-0.5">or click to browse</p>
          </div>

          <div className="flex flex-wrap justify-center gap-2 mt-2">
            {FILE_TYPE_INFO.map((type) => (
              <span
                key={type.label}
                className={`text-xs px-2 py-0.5 bg-gray-800 rounded border border-gray-600 ${type.color}`}
              >
                {type.label}: {type.exts}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
