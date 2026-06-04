import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Chat } from "@/components/Chat";
import type { ChatHandlers } from "@/lib/chatClient";

const fakeStream = vi.fn(async (_m: string, h: ChatHandlers) => {
  h.onToken("보증금은 우선변제[1] 됩니다.");
  h.onDone("보증금은 우선변제[1] 됩니다.", [
    { n: 1, title: "주택임대차보호법 제3조의2", ref: "제3조의2", url: "https://law/1", source_type: "법령" },
  ]);
});

describe("Chat", () => {
  it("sends a question and renders the streamed answer + source", async () => {
    render(<Chat stream={fakeStream} />);
    await userEvent.type(screen.getByRole("textbox"), "보증금 못 받았어요");
    await userEvent.click(screen.getByRole("button", { name: /전송/ }));

    expect(await screen.findByText(/우선변제\[1\] 됩니다\./)).toBeInTheDocument();
    expect(screen.getByText("보증금 못 받았어요")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /주택임대차보호법 제3조의2/ })).toHaveAttribute(
      "href",
      "https://law/1",
    );
  });
});
