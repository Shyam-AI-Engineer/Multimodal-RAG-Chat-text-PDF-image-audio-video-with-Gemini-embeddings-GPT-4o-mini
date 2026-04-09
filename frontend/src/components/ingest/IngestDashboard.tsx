"use client";

import { useIngest } from "@/hooks/useIngest";
import { FileUploader } from "./FileUploader";
import { IngestedFiles } from "./IngestedFiles";
import { IngestionStatus } from "./IngestionStatus";
import { TextInput } from "./TextInput";

export function IngestDashboard() {
  const {
    uploadItems,
    ingestedFiles,
    isLoadingFiles,
    addFiles,
    submitText,
    removeUploadItem,
    clearCompleted,
    refreshIngestedFiles,
    textSubmitError,
  } = useIngest();

  const hasCompleted = uploadItems.some(
    (item) => item.status === "success" || item.status === "error"
  );
  const activeCount = uploadItems.filter(
    (item) => item.status === "uploading" || item.status === "processing"
  ).length;

  return (
    <div className="flex flex-col lg:flex-row gap-6 p-6 h-full overflow-auto">
      {/* Left column — upload and text input */}
      <div className="flex-1 min-w-0 space-y-6">
        {/* File upload */}
        <section aria-labelledby="file-upload-heading">
          <div className="flex items-center justify-between mb-3">
            <h2 id="file-upload-heading" className="text-gray-200 font-medium">
              Upload Files
            </h2>
            {activeCount > 0 && (
              <span className="text-blue-400 text-xs animate-pulse">
                {activeCount} file{activeCount > 1 ? "s" : ""} uploading...
              </span>
            )}
          </div>
          <FileUploader onFiles={addFiles} disabled={false} />
        </section>

        {/* Upload queue */}
        {uploadItems.length > 0 && (
          <section aria-labelledby="upload-queue-heading">
            <div className="flex items-center justify-between mb-3">
              <h2 id="upload-queue-heading" className="text-gray-200 font-medium text-sm">
                Upload Queue ({uploadItems.length})
              </h2>
              {hasCompleted && (
                <button
                  onClick={clearCompleted}
                  className="text-gray-400 hover:text-gray-200 text-xs transition-colors"
                >
                  Clear completed
                </button>
              )}
            </div>
            <div className="space-y-2">
              {uploadItems.map((item) => (
                <IngestionStatus
                  key={item.id}
                  item={item}
                  onRemove={removeUploadItem}
                />
              ))}
            </div>
          </section>
        )}

        {/* Text input */}
        <section aria-labelledby="text-input-heading">
          <h2 id="text-input-heading" className="text-gray-200 font-medium mb-3">
            Paste Raw Text
          </h2>
          <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
            <TextInput
              onSubmit={submitText}
              error={textSubmitError}
            />
          </div>
        </section>
      </div>

      {/* Right column — ingested files list */}
      <div className="lg:w-80 xl:w-96 flex-shrink-0">
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4 sticky top-0">
          <IngestedFiles
            files={ingestedFiles}
            isLoading={isLoadingFiles}
            onRefresh={refreshIngestedFiles}
          />
        </div>
      </div>
    </div>
  );
}
