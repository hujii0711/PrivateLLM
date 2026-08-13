# 계획 2B — Next.js 채팅 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plan 2A의 FastAPI `/chat` SSE 엔드포인트를 소비하는 Next.js 채팅 UI를 만든다. 사용자가 질문하면 답변 토큰이 실시간 스트리밍되고, 완료 시 출처 카드(`[n]` → 법령·판례 링크)와 면책 고지가 표시된다. 브라우저에서 데모 가능한 RAG 챗봇 완성이 산출물.

**Architecture:** `apps/web`(Next.js App Router + TypeScript + Tailwind). 핵심 로직은 순수·테스트 가능 단위로 분리: `lib/sse.ts`(SSE 프레임 파서), `lib/chatClient.ts`(fetch POST + 스트림 리더), `hooks/useChat.ts`(상태 머신). UI는 `components/*`(SourceCard, MessageBubble, ChatInput, Chat). 브라우저 EventSource는 GET만 지원하므로 **POST+SSE는 `fetch` + `ReadableStream` 리더**로 소비한다.

**Tech Stack:** Next.js 15(App Router), React 19, TypeScript, Tailwind CSS v4, Vitest + @testing-library/react + jsdom(단위·컴포넌트 테스트), npm.

**Scope (YAGNI):** 단일 질의→단일 답변(멀티턴 히스토리 누적 표시는 하되 서버로 history 안 보냄 — `/chat`은 단일 message만 받음). 인증·세션 저장·마크다운 렌더링·다크모드 토글은 범위 밖. E2E(Playwright)는 범위 밖 — 단위/컴포넌트 테스트 + 수동 브라우저 스모크로 검증.

**전제:** Plan 2A 완료(`apps/api`의 `/chat` SSE 동작). API 계약:
- `POST /chat` body `{"message": string}` → SSE 스트림. 프레임: `data: {"type":"token","text":string}` (0개 이상) → `data: {"type":"done","answer":string,"sources":[{"n":int,"title":string,"ref":string,"url":string,"source_type":string}]}`.
- `GET /health` → `{"status":"ok"}`. CORS는 `http://localhost:3000` 허용.
- 참고: JSON은 `ensure_ascii=False` 단일 라인(answer 내 줄바꿈은 `\n` 이스케이프), 프레임 구분은 빈 줄(`\n\n`).

---

## File Structure

```
apps/web/
├── package.json
├── tsconfig.json
├── next.config.ts
├── vitest.config.ts
├── vitest.setup.ts
├── postcss.config.mjs            # tailwind v4
├── .env.local.example            # NEXT_PUBLIC_API_BASE
├── app/
│   ├── layout.tsx
│   ├── page.tsx                  # Chat 컨테이너 마운트
│   └── globals.css               # tailwind import
├── lib/
│   ├── types.ts                  # ChatEvent, Source, Message
│   ├── sse.ts                    # SSEParser (순수, TDD)
│   └── chatClient.ts             # streamChat(message, handlers) (TDD, fetch mock)
├── hooks/
│   └── useChat.ts                # 상태 머신 (TDD, client mock)
└── components/
    ├── SourceCard.tsx            # 출처 카드 (TDD/RTL)
    ├── MessageBubble.tsx         # 메시지 버블 (TDD/RTL)
    ├── ChatInput.tsx             # 입력창 (TDD/RTL)
    └── Chat.tsx                  # 컨테이너: useChat + 리스트 + 입력 (TDD/RTL)
```

테스트는 소스 옆 `*.test.ts(x)`로 둔다(Vitest 기본 수집).

---

## Task 0: Next.js 스캐폴딩 + Vitest + 워크스페이스 제외

**Files:**
- Create: `apps/web/*` (create-next-app 산출물)
- Create: `apps/web/vitest.config.ts`, `vitest.setup.ts`
- Modify: `pyproject.toml` (repo root — uv 워크스페이스에서 apps/web 제외)

- [ ] **Step 1: uv 워크스페이스에서 apps/web 제외 (Python 멤버 오인 방지)**

`pyproject.toml` (repo root) 를 다음으로 수정:
```toml
[tool.uv.workspace]
members = ["pipelines", "packages/*", "apps/*"]
exclude = ["apps/web"]
```
검증: `cd /Users/fujii0711/Claude/privateLLM && uv sync` → 에러 없이 완료(apps/web는 Python 멤버에서 빠짐).

- [ ] **Step 2: Next.js 앱 생성 (비대화형)**

Run:
```bash
cd /Users/fujii0711/Claude/privateLLM/apps
npx --yes create-next-app@latest web \
  --typescript --tailwind --app --no-src-dir --eslint --use-npm --turbopack --import-alias "@/*" --yes
```
Expected: `apps/web/`에 Next.js 앱 생성(package.json, app/, tsconfig.json, next.config.ts, tailwind/postcss). npm 의존성 설치됨.

> create-next-app 플래그가 버전에 따라 다르면(예: `--turbopack` 미지원), 해당 플래그만 빼고 재실행. 핵심은 TypeScript + Tailwind + App Router + `@/*` alias. 생성 후 `apps/web/app/page.tsx`의 기본 보일러플레이트는 Task 7에서 교체.

- [ ] **Step 3: 테스트 도구 설치**

Run:
```bash
cd /Users/fujii0711/Claude/privateLLM/apps/web
npm install -D vitest@^2 @vitejs/plugin-react@^4 jsdom@^25 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14
```

- [ ] **Step 4: Vitest 설정**

`apps/web/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
  resolve: {
    alias: { "@": resolve(__dirname, ".") },
  },
});
```

`apps/web/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

`apps/web/package.json`의 `"scripts"`에 추가(기존 dev/build/start/lint 유지):
```json
"test": "vitest run",
"test:watch": "vitest"
```

`apps/web/.env.local.example`:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- [ ] **Step 5: 스모크 — 빈 테스트가 도는지 확인**

임시 파일 `apps/web/lib/smoke.test.ts`:
```ts
import { describe, it, expect } from "vitest";
describe("smoke", () => {
  it("runs", () => { expect(1 + 1).toBe(2); });
});
```
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test`
Expected: 1 passed. 확인 후 `rm apps/web/lib/smoke.test.ts`.

- [ ] **Step 6: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git checkout -b plan2b-web
# apps/web/.gitignore는 create-next-app이 생성(node_modules/.next 등 무시). 루트 .gitignore에도 node_modules가 있음.
git add pyproject.toml apps/web
git reset -- apps/web/node_modules 2>/dev/null || true
git commit -m "chore(web): scaffold Next.js app + Vitest, exclude from uv workspace"
```
> `node_modules`/`.next`는 gitignore되어야 함. 커밋 전 `git status`로 node_modules가 스테이지 안 됐는지 확인.

---

## Task 1: 타입 + SSE 파서

**Files:**
- Create: `apps/web/lib/types.ts`
- Create: `apps/web/lib/sse.ts`
- Test: `apps/web/lib/sse.test.ts`

SSE 프레임(`data: <json>\n\n`)을 청크 경계와 무관하게 누적 파싱하는 순수 파서. 가장 중요한 테스트 가능 단위.

- [ ] **Step 1: 실패하는 테스트** — `apps/web/lib/sse.test.ts`:
```ts
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
    expect(p.push(": ping\n\ndata: y\n\nda')).toEqual(["y"]);
    expect(p.push('ta: z\n\n')).toEqual(["z"]);
  });
});
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- sse`
Expected: FAIL — Cannot find module '@/lib/sse'.

- [ ] **Step 3: 구현**

`apps/web/lib/types.ts`:
```ts
export interface Source {
  n: number;
  title: string;
  ref: string;
  url: string;
  source_type: string;
}

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "done"; answer: string; sources: Source[] };

export interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: Source[];
  streaming?: boolean;
}
```

`apps/web/lib/sse.ts`:
```ts
/** POST+SSE 응답을 청크 단위로 받아 완성된 data 페이로드(JSON 문자열)를 반환하는 파서. */
export class SSEParser {
  private buf = "";

  push(chunk: string): string[] {
    this.buf += chunk.replace(/\r\n/g, "\n");
    const out: string[] = [];
    let idx: number;
    while ((idx = this.buf.indexOf("\n\n")) !== -1) {
      const frame = this.buf.slice(0, idx);
      this.buf = this.buf.slice(idx + 2);
      const data = frame
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).replace(/^ /, ""))
        .join("\n");
      if (data) out.push(data);
    }
    return out;
  }
}
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- sse`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/lib/types.ts apps/web/lib/sse.ts apps/web/lib/sse.test.ts
git commit -m "feat(web): add types + SSE frame parser"
```

---

## Task 2: 채팅 클라이언트 (fetch POST + 스트림)

**Files:**
- Create: `apps/web/lib/chatClient.ts`
- Test: `apps/web/lib/chatClient.test.ts`

`streamChat`은 `/chat`에 POST하고 응답 본문 스트림을 `SSEParser`로 파싱해 핸들러로 토큰/완료/에러를 전달한다.

- [ ] **Step 1: 실패하는 테스트** — `apps/web/lib/chatClient.test.ts`:
```ts
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
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- chatClient`
Expected: FAIL — Cannot find module '@/lib/chatClient'.

- [ ] **Step 3: 구현** — `apps/web/lib/chatClient.ts`:
```ts
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
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- chatClient`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/lib/chatClient.ts apps/web/lib/chatClient.test.ts
git commit -m "feat(web): add streaming chat client (fetch POST + SSE)"
```

---

## Task 3: useChat 훅 (상태 머신)

**Files:**
- Create: `apps/web/hooks/useChat.ts`
- Test: `apps/web/hooks/useChat.test.tsx`

메시지 목록·전송·스트리밍 상태를 관리. `streamChat`을 주입 가능하게 해서 테스트한다.

- [ ] **Step 1: 실패하는 테스트** — `apps/web/hooks/useChat.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
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
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- useChat`
Expected: FAIL — Cannot find module '@/hooks/useChat'.

- [ ] **Step 3: 구현** — `apps/web/hooks/useChat.ts`:
```ts
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
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- useChat`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/hooks/useChat.ts apps/web/hooks/useChat.test.tsx
git commit -m "feat(web): add useChat state hook"
```

---

## Task 4: SourceCard 컴포넌트

**Files:**
- Create: `apps/web/components/SourceCard.tsx`
- Test: `apps/web/components/SourceCard.test.tsx`

- [ ] **Step 1: 실패하는 테스트** — `apps/web/components/SourceCard.test.tsx`:
```tsx
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
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- SourceCard`
Expected: FAIL — Cannot find module '@/components/SourceCard'.

- [ ] **Step 3: 구현** — `apps/web/components/SourceCard.tsx`:
```tsx
import type { Source } from "@/lib/types";

export function SourceCard({ source }: { source: Source }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-gray-200 p-3 text-sm hover:bg-gray-50"
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold text-blue-600">[{source.n}]</span>
        <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
          {source.source_type}
        </span>
      </div>
      <div className="mt-1 text-gray-800">{source.title}</div>
    </a>
  );
}
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- SourceCard`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/components/SourceCard.tsx apps/web/components/SourceCard.test.tsx
git commit -m "feat(web): add SourceCard component"
```

---

## Task 5: MessageBubble 컴포넌트

**Files:**
- Create: `apps/web/components/MessageBubble.tsx`
- Test: `apps/web/components/MessageBubble.test.tsx`

사용자/어시스턴트 메시지를 렌더. 어시스턴트 메시지는 답변 본문(줄바꿈 보존) + 스트리밍 표시 + 출처 카드 목록.

- [ ] **Step 1: 실패하는 테스트** — `apps/web/components/MessageBubble.test.tsx`:
```tsx
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
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- MessageBubble`
Expected: FAIL — Cannot find module '@/components/MessageBubble'.

- [ ] **Step 3: 구현** — `apps/web/components/MessageBubble.tsx`:
```tsx
import type { Message } from "@/lib/types";
import { SourceCard } from "./SourceCard";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser ? "bg-blue-600 text-white" : "bg-white text-gray-900 shadow"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{message.text}</p>

        {message.streaming && (
          <span
            data-testid="streaming-indicator"
            className="ml-1 inline-block h-3 w-2 animate-pulse bg-current align-middle"
          />
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div data-testid="sources" className="mt-3 space-y-2">
            <div className="text-xs font-semibold text-gray-500">출처</div>
            {message.sources.map((s) => (
              <SourceCard key={s.n} source={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- MessageBubble`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/components/MessageBubble.tsx apps/web/components/MessageBubble.test.tsx
git commit -m "feat(web): add MessageBubble component"
```

---

## Task 6: ChatInput 컴포넌트

**Files:**
- Create: `apps/web/components/ChatInput.tsx`
- Test: `apps/web/components/ChatInput.test.tsx`

- [ ] **Step 1: 실패하는 테스트** — `apps/web/components/ChatInput.test.tsx`:
```tsx
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
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- ChatInput`
Expected: FAIL — Cannot find module '@/components/ChatInput'.

- [ ] **Step 3: 구현** — `apps/web/components/ChatInput.tsx`:
```tsx
"use client";
import { useState, type FormEvent } from "react";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (text: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue("");
  }

  return (
    <form onSubmit={submit} className="flex gap-2">
      <input
        type="text"
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        placeholder="보증금 반환에 대해 물어보세요…"
        className="flex-1 rounded-full border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-full bg-blue-600 px-5 py-2 font-medium text-white disabled:opacity-50"
      >
        전송
      </button>
    </form>
  );
}
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- ChatInput`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/components/ChatInput.tsx apps/web/components/ChatInput.test.tsx
git commit -m "feat(web): add ChatInput component"
```

---

## Task 7: Chat 컨테이너 + 페이지 연결

**Files:**
- Create: `apps/web/components/Chat.tsx`
- Test: `apps/web/components/Chat.test.tsx`
- Modify: `apps/web/app/page.tsx` (Chat 마운트)
- Modify: `apps/web/app/layout.tsx` (제목/언어)

- [ ] **Step 1: 실패하는 테스트** — `apps/web/components/Chat.test.tsx`:
```tsx
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
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- Chat`
Expected: FAIL — Cannot find module '@/components/Chat'.

- [ ] **Step 3: 구현**

`apps/web/components/Chat.tsx`:
```tsx
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
            예: “전세 보증금을 집주인이 안 돌려줘요. 어떻게 해야 하나요?”
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
```

`apps/web/app/page.tsx` (전체 교체):
```tsx
import { Chat } from "@/components/Chat";

export default function Home() {
  return <Chat />;
}
```

`apps/web/app/layout.tsx` — `metadata`의 title을 `"보증금 반환 상담 챗봇"`으로, `<html lang="en">`을 `<html lang="ko">`로 수정(나머지 create-next-app 기본 구조 유지).

- [ ] **Step 4: 통과 확인 + 빌드 검증**
Run:
```bash
cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test -- Chat && npm run build
```
Expected: Chat 테스트 PASS (1 passed); `npm run build` 성공(타입 에러·린트 에러 없이 프로덕션 빌드 완료).

- [ ] **Step 5: 전체 테스트**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/web && npm run test`
Expected: 모든 테스트 통과(sse 5 + chatClient 3 + useChat 2 + SourceCard 1 + MessageBubble 4 + ChatInput 3 + Chat 1).

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/web/components/Chat.tsx apps/web/components/Chat.test.tsx apps/web/app/page.tsx apps/web/app/layout.tsx
git commit -m "feat(web): add Chat container + wire page"
```

---

## Task 8: 라이브 엔드투엔드 스모크 (api + web)

**Files:** 없음(검증 전용). 코드 변경이 필요하면 별도 커밋.

실제 백엔드(MLX Qwen + Chroma)와 프론트엔드를 함께 띄워 브라우저에서 검증한다.

- [ ] **Step 1: 백엔드 기동(백그라운드)**
```bash
cd /Users/fujii0711/Claude/privateLLM
uv run --package api uvicorn api.main:app --port 8000 > /tmp/api_web_smoke.log 2>&1 &
echo $! > /tmp/api_web.pid
sleep 6
curl -s http://localhost:8000/health   # {"status":"ok"} 확인
```

- [ ] **Step 2: 프론트엔드 환경 + 기동**
```bash
cd /Users/fujii0711/Claude/privateLLM/apps/web
cp -n .env.local.example .env.local    # NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev > /tmp/web_smoke.log 2>&1 &
echo $! > /tmp/web.pid
sleep 6
curl -s -I http://localhost:3000 | head -1   # HTTP/1.1 200 OK 확인
```

- [ ] **Step 3: 브라우저 수동 검증**
브라우저에서 `http://localhost:3000` 열기. 입력창에 다음을 보내고 관찰:
> "전세 보증금을 집주인이 안 돌려줘요. 어떻게 해야 하나요?"

확인 항목(체크리스트 — 실제 관찰 결과를 보고):
- [ ] 사용자 메시지가 오른쪽 버블로 표시됨
- [ ] 어시스턴트 답변이 **토큰 단위로 스트리밍**되며 스트리밍 인디케이터가 보임
- [ ] 답변이 ①상황요약 ②적용법리 ③다음절차 상담형 구조
- [ ] 답변에 `[1]` 등 인용 마커가 있고, 하단 **출처 카드**에 주택임대차보호법 제3조의2 등 제목+링크 표시
- [ ] 출처 카드 링크가 law.go.kr로 새 탭 열림
- [ ] 면책 고지 문구가 답변 말미에 있음
- [ ] 전송 중 입력창/버튼 비활성화, 완료 후 재활성화

> 첫 요청은 모델 로딩으로 십수 초~수십 초 지연(이후 빠름). CORS 에러가 콘솔에 뜨면 `apps/api/src/api/main.py`의 allow_origins에 `http://localhost:3000`이 있는지 확인(이미 있음).

- [ ] **Step 4: 종료**
```bash
kill "$(cat /tmp/api_web.pid)" "$(cat /tmp/web.pid)" 2>/dev/null
```

- [ ] **Step 5: (관찰 결과만 기록 — 코드 변경 없으면 커밋 없음)**
스모크에서 버그를 발견하면 해당 task로 돌아가 수정·재검증 후 커밋. 통과면 Plan 2B 완료.

---

## 완료 기준 (Definition of Done)

- [ ] `cd apps/web && npm run test` 전체 통과(19개: sse 5, chatClient 3, useChat 2, SourceCard 1, MessageBubble 4, ChatInput 3, Chat 1).
- [ ] `npm run build` 성공(타입/린트 에러 없음).
- [ ] `uv run --package api uvicorn ...` + `npm run dev` 동시 기동 후 브라우저에서 보증금 질의 → 스트리밍 답변 + 출처 카드 + 면책 고지가 정상 표시.
- [ ] uv 워크스페이스 `uv sync`가 apps/web 때문에 깨지지 않음(exclude 적용).

이 시점에서 **브라우저로 데모 가능한 RAG 챗봇**이 완성된다. Plan 1(데이터)→2A(API)→2B(UI)로 RAG 베이스라인 전체가 동작.

---

## 후속 계획으로의 인계 (Plan 3)

- Plan 3(평가 + QLoRA)은 백엔드 중심이라 이 UI는 그대로 사용. QLoRA 어댑터 적용 모델로 교체해도 `/chat` 계약 불변 → UI 변경 불필요.
- 미보완(2A 리뷰 인계, UI에서 체감되는 것): 스트림 중 LLM 오류 시 백엔드가 error 이벤트를 안 보냄 → 현재 UI는 onError로 "오류가 발생했습니다" 표시(클라이언트 측 fetch 실패 시). 백엔드 error 이벤트 추가 시 `ChatEvent`에 `{type:"error"}` 케이스 추가 권장.
- 배포 시: `NEXT_PUBLIC_API_BASE`와 백엔드 CORS allow_origins를 실제 도메인으로.
