import type { Message } from "@/lib/types";
import { SourceCard } from "./SourceCard";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser ? "bg-blue-600 text-white" : "bg-white text-gray-900 shadow"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.text}</p>

        {message.streaming && (
          <span
            data-testid="streaming-indicator"
            className="ml-1 inline-block h-3 w-2 animate-pulse bg-current align-middle"
          />
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div data-testid="sources" className="mt-3 space-y-2">
            <div className="text-xs font-semibold text-gray-500">출처</div>
            {message.sources.map((s) => (
              <SourceCard key={s.n} source={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
