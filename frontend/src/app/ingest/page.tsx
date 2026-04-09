import { IngestDashboard } from "@/components/ingest/IngestDashboard";
import { Header } from "@/components/layout/Header";

export default function IngestPage() {
  return (
    <div className="flex flex-col h-full min-h-0">
      <Header
        title="Ingest Data"
        subtitle="Upload files or paste text to add to your knowledge base"
      />
      <div className="flex-1 min-h-0 overflow-auto">
        <IngestDashboard />
      </div>
    </div>
  );
}
