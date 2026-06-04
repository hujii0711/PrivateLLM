"use client";
import { useCallback, useState } from "react";
import { streamChat as defaultStream } from "@/lib/chatClient";
import type { ChatHandlers } from "@/lib/chatClient";
import type { Message, Source } from "@/lib/types";

type StreamFn = (message: string, handlers: ChatHandlers) => Promise<void>;

export function useChat(opts?: { stream?: StreamFn }) {
  const stream = opts?.stream ?? defaultStream;
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);

  const send = useCallback(
    async (raw: string) => {
      const message = raw.trim();
      if (!message || busy) return;

      setMessages((m) => [
        ...m,
        { role: "user", text: message },
        { role: "assistant", text: "", streaming: true },
      ]);
      setBusy(true);

      const patchLast = (fn: (msg: Message) => Message) =>
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = fn(copy[copy.length - 1]);
          return copy;
        });

      await stream(message, {
        onToken: (t) => patchLast((msg) => ({ ...msg, text: msg.text + t })),
        onDone: (answer: string, sources: Source[]) =>
          patchLast((msg) => ({ ...msg, text: answer, sources, streaming: false })),
        onError: () =>
          patchLast((msg) => ({
            ...msg,
            text: msg.text || "오류가 발생했습니다. 다시 시도해 주세요.",
            streaming: false,
          })),
      });
      setBusy(false);
    },
    [busy, stream],
  );

  return { messages, busy, send };
}
