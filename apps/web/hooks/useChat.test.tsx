import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChat } from "@/hooks/useChat";
import type { ChatHandlers } from "@/lib/chatClient";

// streamChat를 가짜로 주입: 토큰 2개 후 done
const fakeStream = vi.fn(async (_msg: string, h: ChatHandlers) => {
  h.onToken("보증금은 ");
  h.onToken("우선변제[1] 됩니다.");
  h.onDone("보증금은 우선변제[1] 됩니다.", [
    { n: 1, title: "주택임대차보호법 제3조의2", ref: "제3조의2", url: "https://law/1", source_type: "법령" },
  ]);
});

describe("useChat", () => {
  it("appends user + streaming assistant message, then finalizes", async () => {
    const { result } = renderHook(() => useChat({ stream: fakeStream }));

    await act(async () => { await result.current.send("보증금?"); });

    const msgs = result.current.messages;
    expect(msgs[0]).toMatchObject({ role: "user", text: "보증금?" });
    expect(msgs[1].role).toBe("assistant");
    expect(msgs[1].text).toBe("보증금은 우선변제[1] 됩니다.");
    expect(msgs[1].sources?.[0].url).toBe("https://law/1");
    expect(msgs[1].streaming).toBe(false);
    expect(result.current.busy).toBe(false);
  });

  it("ignores empty/whitespace messages", async () => {
    const spy = vi.fn();
    const { result } = renderHook(() => useChat({ stream: spy }));
    await act(async () => { await result.current.send("   "); });
    expect(spy).not.toHaveBeenCalled();
    expect(result.current.messages).toHaveLength(0);
  });
});
