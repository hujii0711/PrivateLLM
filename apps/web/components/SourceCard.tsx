import type { Source } from "@/lib/types";

export function SourceCard({ source }: { source: Source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-gray-200 p-3 text-sm hover:bg-gray-50"
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold text-blue-600">[{source.n}]</span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
          {source.source_type}
        </span>
      </div>
      <div className="mt-1 text-gray-800">{source.title}</div>
    </a>
  );
}
