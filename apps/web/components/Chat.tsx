"use client";
import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import type { ChatHandlers } from "@/lib/chatClient";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";

type StreamFn = (message: string, handlers: ChatHandlers) => Promise<void>;

export function Chat({ stream }: { stream?: StreamFn }) {
  const { messages, busy, send } = useChat(stream ? { stream } : undefined);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="mx-auto flex h-screen max-w-2xl flex-col">
      <header className="border-b p-4">
        <h1 className="text-lg font-bold">주택임대차 보증금 반환 상담</h1>
        <p className="text-xs text-gray-500">
          법령·판례 근거 기반 상담 · 일반적 정보 제공이며 법률 자문이 아닙니다
        </p>
      </header>

      <main className="flex-1 space-y-4 overflow-y-auto bg-gray-50 p-4">
        {messages.length === 0 && (
          <p className="mt-8 text-center text-gray-400">
            예: &ldquo;전세 보증금을 집주인이 안 돌려줘요. 어떻게 해야 하나요?&rdquo;
          </p>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} message={m} />
        ))}
        <div ref={endRef} />
      </main>

      <footer className="border-t p-4">
        <ChatInput onSend={send} disabled={busy} />
      </footer>
    </div>
  );
}
