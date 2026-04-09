import type { SourceReference, SourceType } from "@/lib/types";

interface SourceCardProps {
  source: SourceReference;
  index: number;
}

const SOURCE_TYPE_COLORS: Record<SourceType, string> = {
  text: "bg-blue-900/50 text-blue-300 border-blue-700",
  pdf: "bg-red-900/50 text-red-300 border-red-700",
  image: "bg-purple-900/50 text-purple-300 border-purple-700",
  audio: "bg-green-900/50 text-green-300 border-green-700",
  video: "bg-orange-900/50 text-orange-300 border-orange-700",
};

const SOURCE_TYPE_ICONS: Record<SourceType, string> = {
  text: "T",
  pdf: "P",
  image: "I",
  audio: "A",
  video: "V",
};

function ScoreBar({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${percentage}%` }}
          aria-hidden="true"
        />
      </div>
      <span className="text-xs text-gray-400 tabular-nums w-8 text-right">
        {percentage}%
      </span>
    </div>
  );
}

export function SourceCard({ source, index }: SourceCardProps) {
  const colorClass = SOURCE_TYPE_COLORS[source.source_type] ?? SOURCE_TYPE_COLORS.text;
  const icon = SOURCE_TYPE_ICONS[source.source_type] ?? "?";

  return (
    <article
      className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs"
      aria-label={`Source ${index + 1}: ${source.source_file}`}
    >
      <div className="flex items-start gap-2 mb-2">
        <span
          className={`inline-flex items-center justify-center w-5 h-5 rounded text-xs font-bold border flex-shrink-0 ${colorClass}`}
          aria-label={`Type: ${source.source_type}`}
        >
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-gray-200 font-medium truncate" title={source.source_file}>
            {source.source_file}
          </p>
          <p className="text-gray-500 text-xs">
            {source.source_type} · chunk #{source.chunk_index}
          </p>
        </div>
      </div>

      <ScoreBar score={source.score} />

      {source.content_preview && (
        <p className="mt-2 text-gray-400 line-clamp-2 leading-relaxed">
          {source.content_preview}
        </p>
      )}
    </article>
  );
}
