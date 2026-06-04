import { SSEParser } from "./sse";
import type { ChatEvent, Source } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface ChatHandlers {
  onToken: (text: string) => void;
  onDone: (answer: string, sources: Source[]) => void;
  onError: (err: unknown) => void;
}

export async function streamChat(message: string, h: ChatHandlers): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!resp.ok || !resp.body) {
      h.onError(new Error(`chat failed: ${resp.status}`));
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    const parser = new SSEParser();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const payload of parser.push(decoder.decode(value, { stream: true }))) {
        const ev = JSON.parse(payload) as ChatEvent;
        if (ev.type === "token") h.onToken(ev.text);
        else if (ev.type === "done") h.onDone(ev.answer, ev.sources);
      }
    }
  } catch (err) {
    h.onError(err);
  }
}
