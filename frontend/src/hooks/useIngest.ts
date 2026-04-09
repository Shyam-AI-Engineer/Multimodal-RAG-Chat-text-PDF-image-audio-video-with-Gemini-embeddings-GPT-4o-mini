"use client";

import { useCallback, useEffect, useState } from "react";
import { getIngestedFiles, ingestFile, ingestText } from "@/lib/api";
import type { IngestedFileRecord, UploadItem, UploadStatus } from "@/lib/types";

function generateId(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

interface UseIngestReturn {
  uploadItems: UploadItem[];
  ingestedFiles: IngestedFileRecord[];
  isLoadingFiles: boolean;
  addFiles: (files: File[]) => void;
  submitText: (text: string, sourceName?: string) => Promise<void>;
  removeUploadItem: (id: string) => void;
  clearCompleted: () => void;
  refreshIngestedFiles: () => Promise<void>;
  textSubmitError: string | null;
  isSubmittingText: boolean;
}

export function useIngest(): UseIngestReturn {
  const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
  const [ingestedFiles, setIngestedFiles] = useState<IngestedFileRecord[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [textSubmitError, setTextSubmitError] = useState<string | null>(null);
  const [isSubmittingText, setIsSubmittingText] = useState(false);

  const updateItem = useCallback(
    (id: string, updates: Partial<UploadItem>) => {
      setUploadItems((prev) =>
        prev.map((item) => (item.id === id ? { ...item, ...updates } : item))
      );
    },
    []
  );

  const processFile = useCallback(
    async (item: UploadItem) => {
      updateItem(item.id, { status: "uploading" as UploadStatus, progress: 0, message: "Uploading..." });

      try {
        const response = await ingestFile(item.file, (progress) => {
          updateItem(item.id, {
            progress,
            message: `Uploading... ${progress}%`,
            status: "uploading" as UploadStatus,
          });
        });

        updateItem(item.id, {
          status: "success" as UploadStatus,
          progress: 100,
          message: response.message,
          response,
        });
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : "Upload failed";
        updateItem(item.id, {
          status: "error" as UploadStatus,
          progress: 0,
          message: errMsg,
          error: errMsg,
        });
      }
    },
    [updateItem]
  );

  const addFiles = useCallback(
    (files: File[]) => {
      const newItems: UploadItem[] = files.map((file) => ({
        id: generateId(),
        file,
        status: "idle" as UploadStatus,
        progress: 0,
        message: "Queued",
      }));

      setUploadItems((prev) => [...prev, ...newItems]);

      // Process all files
      newItems.forEach((item) => {
        processFile(item);
      });
    },
    [processFile]
  );

  const refreshIngestedFiles = useCallback(async () => {
    setIsLoadingFiles(true);
    try {
      const response = await getIngestedFiles();
      setIngestedFiles(response.files);
    } catch {
      // Silently fail — backend may not be running
    } finally {
      setIsLoadingFiles(false);
    }
  }, []);

  const submitText = useCallback(
    async (text: string, sourceName: string = "manual_input") => {
      if (!text.trim()) return;

      setTextSubmitError(null);
      setIsSubmittingText(true);

      try {
        await ingestText({ text: text.trim(), source_name: sourceName });
        // Refresh the ingested files list
        await refreshIngestedFiles();
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : "Text ingestion failed";
        setTextSubmitError(errMsg);
        throw err;
      } finally {
        setIsSubmittingText(false);
      }
    },
    [refreshIngestedFiles]
  );

  const removeUploadItem = useCallback((id: string) => {
    setUploadItems((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setUploadItems((prev) =>
      prev.filter((item) => item.status !== "success" && item.status !== "error")
    );
  }, []);

  // Load ingested files on mount
  useEffect(() => {
    refreshIngestedFiles();
  }, [refreshIngestedFiles]);

  // Refresh after successful uploads
  useEffect(() => {
    const hasSuccessful = uploadItems.some((item) => item.status === "success");
    if (hasSuccessful) {
      refreshIngestedFiles();
    }
  }, [uploadItems, refreshIngestedFiles]);

  return {
    uploadItems,
    ingestedFiles,
    isLoadingFiles,
    addFiles,
    submitText,
    removeUploadItem,
    clearCompleted,
    refreshIngestedFiles,
    textSubmitError,
    isSubmittingText,
  };
}
