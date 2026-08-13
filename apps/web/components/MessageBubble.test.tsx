import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble } from "@/components/MessageBubble";
import type { Message } from "@/lib/types";

describe("MessageBubble", () => {
  it("renders a user message", () => {
    const m: Message = { role: "user", text: "보증금 못 받았어요" };
    render(<MessageBubble message={m} />);
    expect(screen.getByText("보증금 못 받았어요")).toBeInTheDocument();
  });

  it("renders assistant answer with source cards", () => {
    const m: Message = {
      role: "assistant",
      text: "보증금은 우선변제[1] 됩니다.",
      streaming: false,
      sources: [{ n: 1, title: "주택임대차보호법 제3조의2", ref: "제3조의2",
        url: "https://law/1", source_type: "법령" }],
    };
    render(<MessageBubble message={m} />);
    expect(screen.getByText(/우선변제\[1\] 됩니다\./)).toBeInTheDocument();
    expect(screen.getByText(/주택임대차보호법 제3조의2/)).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "https://law/1");
  });

  it("shows a streaming indicator while streaming", () => {
    const m: Message = { role: "assistant", text: "보증금은", streaming: true };
    render(<MessageBubble message={m} />);
    expect(screen.getByTestId("streaming-indicator")).toBeInTheDocument();
  });

  it("does not show sources section when there are none", () => {
    const m: Message = { role: "assistant", text: "답변", streaming: false };
    render(<MessageBubble message={m} />);
    expect(screen.queryByTestId("sources")).not.toBeInTheDocument();
  });
});
