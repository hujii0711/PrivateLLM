import { describe, it, expect } from "vitest";
import { SSEParser } from "@/lib/sse";

describe("SSEParser", () => {
  it("emits a complete frame's data payload", () => {
    const p = new SSEParser();
    expect(p.push('data: {"type":"token","text":"a"}\n\n')).toEqual([
      '{"type":"token","text":"a"}',
    ]);
  });

  it("buffers a partial frame across chunks", () => {
    const p = new SSEParser();
    expect(p.push('data: {"type":"to')).toEqual([]);
    expect(p.push('ken","text":"a"}\n\n')).toEqual(['{"type":"token","text":"a"}']);
  });

  it("emits multiple frames from one chunk", () => {
    const p = new SSEParser();
    expect(p.push('data: 1\n\ndata: 2\n\n')).toEqual(["1", "2"]);
  });

  it("normalizes CRLF line endings", () => {
    const p = new SSEParser();
    expect(p.push('data: x\r\n\r\n')).toEqual(["x"]);
  });

  it("ignores non-data lines and keeps leftover", () => {
    const p = new SSEParser();
    expect(p.push(': ping\n\ndata: y\n\nda')).toEqual(["y"]);
    expect(p.push('ta: z\n\n')).toEqual(["z"]);
  });
});
