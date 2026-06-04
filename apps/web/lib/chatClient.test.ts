import { describe, it, expect, vi, afterEach } from "vitest";
import { streamChat } from "@/lib/chatClient";

function streamFrom(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) controller.enqueue(enc.encode(chunks[i++]));
      else controller.close();
    },
  });
}

function mockFetchOk(chunks: string[]) {
  return vi.fn().mockResolvedValue(
    new Response(streamFrom(chunks), { status: 200 }),
  );
}

afterEach(() => vi.restoreAllMocks());

describe("streamChat", () => {
  it("calls onToken per token then onDone with answer+sources", async () => {
    const frames = [
      'data: {"type":"token","text":"보증금은 "}\n\n',
      'data: {"type":"token","text":"우선변제[1] 됩니다."}\n\n',
      'data: {"type":"done","answer":"보증금은 우선변제[1] 됩니다.","sources":[{"n":1,"title":"주택임대차보호법 제3조의2","ref":"제3조의2","url":"https://law/1","source_type":"법령"}]}\n\n',
    ];
    vi.stubGlobal("fetch", mockFetchOk(frames));

    const tokens: string[] = [];
    let done: { answer: string; sources: unknown[] } | null = null;
    await streamChat("보증금?", {
      onToken: (t) => tokens.push(t),
      onDone: (a, s) => { done = { answer: a, sources: s }; },
      onError: () => { throw new Error("should not error"); },
    });

    expect(tokens.join("")).toBe("보증금은 우선변제[1] 됩니다.");
    expect(done!.answer).toContain("우선변제");
    expect((done!.sources[0] as { url: string }).url).toBe("https://law/1");
  });

  it("posts the message as JSON to /chat", async () => {
    const fetchMock = mockFetchOk(['data: {"type":"done","answer":"x","sources":[]}\n\n']);
    vi.stubGlobal("fetch", fetchMock);
    await streamChat("질문", { onToken: () => {}, onDone: () => {}, onError: () => {} });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/chat$/);
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ message: "질문" });
  });

  it("calls onError on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("nope", { status: 500 })));
    let errored = false;
    await streamChat("q", { onToken: () => {}, onDone: () => {}, onError: () => { errored = true; } });
    expect(errored).toBe(true);
  });
});
