import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "@/components/ChatInput";

describe("ChatInput", () => {
  it("submits trimmed text and clears the field", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} disabled={false} />);
    const box = screen.getByRole("textbox");
    await userEvent.type(box, "  보증금 질문  ");
    await userEvent.click(screen.getByRole("button", { name: /전송|보내기|send/i }));
    expect(onSend).toHaveBeenCalledWith("보증금 질문");
    expect(box).toHaveValue("");
  });

  it("does not submit empty input", async () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} disabled={false} />);
    await userEvent.click(screen.getByRole("button"));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables input and button while disabled", () => {
    render(<ChatInput onSend={() => {}} disabled={true} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
