---
name: export-last-response
description: Use when the user asks to save or export the most recent assistant reply to a markdown file (e.g. "방금 응답 내보내줘", "지금 답변 md로 저장", "export the last response"). Triggers on requests to dump/archive the immediately preceding answer to docs/export.
---

# Export Last Response

## Overview
Save the **single most recent assistant response** in this conversation to a markdown file at `docs/export/yyyy-MM-dd-{요약}.md`. Verbatim content only — no added title, frontmatter, or commentary.

## Steps

1. **Target.** The last assistant message containing **text shown to the user**, immediately before this skill was invoked. Ignore tool-call-only turns; not earlier messages, not a summary of several. If there is no prior assistant response, tell the user and stop.

2. **Date.** Today's date as `yyyy-MM-dd`. Use the current date the environment provides (e.g. a `currentDate` / today's-date note); if sources disagree, prefer that injected value.

3. **요약 (filename slug).** Write a concise Korean noun-phrase capturing the response's main topic.
   - 2–6 words, roughly ≤ 30 characters.
   - Replace each run of whitespace with a single hyphen `-`.
   - Remove filesystem-unsafe characters: `/ \ : * ? " < > |` and any leading/trailing punctuation/hyphens.
   - Keep Korean characters as-is (do NOT romanize).

4. **Output dir.** `docs/export/` at the **project root**. Create it if missing (`mkdir -p docs/export`).

5. **Filename.** `{date}-{요약}.md`. If that file already exists, append `-2`, `-3`, … (`2026-06-05-보증금-반환-설명-2.md`). Never overwrite.

6. **Content.** Write the target response's markdown **verbatim** — exactly as it appeared, preserving `①②③`, lists, code blocks, tables. End with a single trailing newline. Do **not** add an H1 title, YAML frontmatter, export note, or any text the user didn't see.

7. **Confirm.** Report the created path to the user (one line).

## Quick Reference

| Item | Rule |
|---|---|
| Source | Immediately-preceding assistant response only |
| Path | `docs/export/{yyyy-MM-dd}-{요약}.md` (project root) |
| 요약 | Korean, ≤~30 chars, spaces→`-`, unsafe chars stripped |
| Collision | Append `-2`, `-3`… never overwrite |
| Content | Verbatim response, nothing added |

## Common Mistakes

- **Adding a heading/frontmatter** — user asked for the response *only*. Write it raw.
- **Romanizing the summary** — keep it Korean (filesystem supports it).
- **Exporting the wrong message** — it's the last response, not the whole conversation or an earlier answer.
- **Overwriting an existing file** — suffix instead.
- **Forgetting to create `docs/export/`** — `mkdir -p` first.
