import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceCard } from "@/components/SourceCard";

const src = { n: 1, title: "주택임대차보호법 제3조의2(보증금의 회수)", ref: "제3조의2",
  url: "https://law.go.kr/x", source_type: "법령" };

describe("SourceCard", () => {
  it("renders citation number, title, type and a link to the url", () => {
    render(<SourceCard source={src} />);
    expect(screen.getByText(/\[1\]/)).toBeInTheDocument();
    expect(screen.getByText(/제3조의2\(보증금의 회수\)/)).toBeInTheDocument();
    expect(screen.getByText("법령")).toBeInTheDocument();
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://law.go.kr/x");
    expect(link).toHaveAttribute("target", "_blank");
  });
});
