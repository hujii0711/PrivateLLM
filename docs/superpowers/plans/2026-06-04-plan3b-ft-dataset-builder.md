# 계획 3B — FT 데이터셋 빌더 (rejection-sampling distillation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** QLoRA 학습용 데이터셋을 합성한다. 평가셋과 겹치지 않는 보증금 반환 질문 풀에 대해, 실제 RAG 파이프라인으로 후보 답변을 다수 생성하고, **평가의 형식 지표를 필터로 재사용**해 상담형 구조·`[n]` 인용·면책을 모두 갖춘 답변만 채택해 MLX chat JSONL(train/valid)로 만든다.

**Architecture:** uv 워크스페이스에 `packages/ftdata` 추가(`rag`·`api`·`eval` 재사용). 질문 풀(평가셋과 disjoint, 커밋) → `api.pipeline.run_chat`로 K개 후보 생성(temp 다양성, 서빙=학습데이터 동일 입력) → `eval.answer_metrics` 형식 필터 + `eval.judge` 근거 점수로 best 채택 → `rag.prompt.build_messages`로 학습 입력 재구성(system+user(근거)) + assistant(답변) → JSONL. 순수 모듈(필터·빌더·분할)은 모델 없이 단위 테스트, 생성·CLI는 라이브.

**Tech Stack:** Python 3.11, uv(workspace), pytest. 라이브: MlxLLM(Qwen2.5-7B) + `data/chroma`.

**Scope (YAGNI):** 이 계획은 **FT 데이터셋 생성만**. QLoRA 학습·A/B는 Plan 3C. 데이터 소스는 **합성 rejection-sampling distillation**(크롤링 아님 — Plan 1이 취약성으로 미룸, FT 목표가 형식이므로 합성이 적합). 규모는 질문 풀 ~30 × 후보 K로 결정되는 PoC 규모(수십~수백; 확장은 질문 풀/teacher 강화로). teacher는 base Qwen 자기-distillation(엄격 rejection) 기본.

**핵심 제약 (Plan 3A 인계):** ⚠️ **train/eval 오염 금지** — 질문 풀은 `packages/eval/eval_set.jsonl`(16문항)과 **겹치지 않아야** 한다(disjointness 테스트로 강제). 측정된 베이스라인 헤드룸(structure_rate 0.75, groundedness 0.69)이 FT의 목표.

**전제:** Plan 1·2A·3A 완료. `data/chroma`(jeonse_deposit), Qwen2.5-7B-4bit 캐시됨.

---

## File Structure

```
packages/ftdata/
├── pyproject.toml                 # deps: rag, api, eval
├── src/ftdata/
│   ├── __init__.py
│   ├── questions.py               # 질문 풀 로더 (eval set과 disjoint)
│   ├── filter.py                  # format_ok (eval.answer_metrics 재사용)
│   ├── builder.py                 # to_chat_example(build_messages 재사용) + train/valid 분할 + write
│   ├── generate.py                # Candidate + generate_candidates (run_chat 재사용)
│   └── cli.py                     # 라이브 빌드 엔트리
├── question_pool.jsonl            # 시드 질문 풀 30 (커밋, eval set과 disjoint)
└── tests/
    ├── conftest.py
    ├── test_questions.py
    ├── test_filter.py
    ├── test_builder.py
    └── test_generate.py
```

학습 데이터 출력(`data/ft/train.jsonl`, `valid.jsonl`)은 gitignore된 `data/`에. 질문 풀(그라운드 트루스)은 패키지에 커밋.

---

## Task 0: packages/ftdata 스캐폴딩

**Files:**
- Create: `packages/ftdata/pyproject.toml`
- Create: `packages/ftdata/src/ftdata/__init__.py` (빈)
- Create: `packages/ftdata/tests/conftest.py` (빈)

- [ ] **Step 1: pyproject** — `packages/ftdata/pyproject.toml`:
```toml
[project]
name = "ftdata"
version = "0.1.0"
description = "주택임대차 보증금 반환 챗봇 — QLoRA 학습 데이터 빌더"
requires-python = ">=3.11"
dependencies = [
    "rag",
    "api",
    "eval",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.uv.sources]
rag = { workspace = true }
api = { workspace = true }
eval = { workspace = true }

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["slow: 실제 모델/인덱스를 쓰는 느린 테스트"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ftdata"]
```

- [ ] **Step 2: 빈 파일** — `packages/ftdata/src/ftdata/__init__.py`, `packages/ftdata/tests/conftest.py` (둘 다 빈).

- [ ] **Step 3: 동기화**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv sync`
Expected: `ftdata` 인식, rag·api·eval 워크스페이스 의존 해결, 에러 없음.

- [ ] **Step 4: pytest + 크로스임포트 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest -q` → "no tests ran".
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package ftdata python -c "from api.pipeline import run_chat; from rag.prompt import build_messages; from eval.answer_metrics import answer_metrics; print('imports ok')"` → "imports ok".

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git checkout -b plan3b-ftdata
git add packages/ftdata pyproject.toml uv.lock
git commit -m "chore(ftdata): scaffold FT dataset builder package"
```

---

## Task 1: 질문 풀 (평가셋과 disjoint)

**Files:**
- Create: `packages/ftdata/question_pool.jsonl`
- Create: `packages/ftdata/src/ftdata/questions.py`
- Test: `packages/ftdata/tests/test_questions.py`

보증금 반환 관련 질문 30개. **평가셋 16문항과 질문 문자열이 하나도 겹치지 않아야** 한다(오염 방지).

- [ ] **Step 1: 질문 풀 작성** — `packages/ftdata/question_pool.jsonl` (한 줄에 `{"question": "..."}`):
```json
{"question":"전입신고를 하지 않았는데 보증금을 보호받을 수 있나요?"}
{"question":"집주인이 보증금 반환을 미룰 때 내용증명은 어떻게 작성하나요?"}
{"question":"집주인이 바뀌었는데 새 집주인에게 보증금을 청구할 수 있나요?"}
{"question":"전세금 반환보증보험은 어떤 경우에 활용할 수 있나요?"}
{"question":"계약 만료 전에 이사를 나가면 보증금을 바로 받을 수 있나요?"}
{"question":"다가구주택인데 임차인들 사이 우선변제 순위는 어떻게 정해지나요?"}
{"question":"임차권등기를 마친 뒤에도 월세를 계속 내야 하나요?"}
{"question":"보증금을 일부만 돌려받았는데 나머지는 어떻게 청구하나요?"}
{"question":"묵시적 갱신이 되면 보증금과 월세는 그대로 유지되나요?"}
{"question":"살던 집이 경매로 넘어가면 임차인은 언제까지 거주할 수 있나요?"}
{"question":"확정일자는 어디서 어떻게 받나요?"}
{"question":"보증금 반환이 지연되면 지연이자를 받을 수 있나요?"}
{"question":"집주인이 계약 갱신을 거절할 수 있는 경우는 어떤 경우인가요?"}
{"question":"보증금 반환 채권을 다른 사람에게 양도할 수 있나요?"}
{"question":"임차주택이 경매에 부쳐질 때 배당요구는 어떻게 신청하나요?"}
{"question":"보증금 증액을 요구받았는데 거절하면 계약이 해지되나요?"}
{"question":"임대차계약서를 분실했는데 확정일자의 효력은 그대로인가요?"}
{"question":"보증금에서 밀린 월세를 공제할 수 있나요?"}
{"question":"임차권등기명령 결정이 나기까지 보통 얼마나 걸리나요?"}
{"question":"집주인이 실거주를 이유로 계약갱신 요구를 거절했습니다."}
{"question":"보증금 반환을 위한 지급명령은 어떻게 진행되나요?"}
{"question":"전세 보증금 일부를 월세로 전환할 때 비율 제한이 있나요?"}
{"question":"임차인이 사망하면 보증금은 누구에게 반환되나요?"}
{"question":"근저당이 설정된 집인데 전세 보증금이 안전한가요?"}
{"question":"주거용 오피스텔도 주택임대차보호법이 적용되나요?"}
{"question":"계약 기간 중인데 집주인이 집을 비워달라고 합니다."}
{"question":"전대(재임대)한 경우 보증금 반환 책임은 누구에게 있나요?"}
{"question":"보증금을 못 받은 상태에서 단전·단수가 되면 어떻게 해야 하나요?"}
{"question":"임차권등기를 한 뒤 다른 집으로 전입신고해도 보증금이 보호되나요?"}
{"question":"전세 계약을 중도 해지하면 중개수수료는 누가 부담하나요?"}
```

- [ ] **Step 2: 로더 + disjointness 테스트** — `packages/ftdata/src/ftdata/questions.py`:
```python
"""질문 풀 로더 (평가셋과 disjoint한 보증금 반환 질문)."""
import json
from pathlib import Path

_POOL = Path(__file__).resolve().parents[2] / "question_pool.jsonl"


def load_questions(path: Path = _POOL) -> list[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line)["question"])
    return out
```

`packages/ftdata/tests/test_questions.py`:
```python
from pathlib import Path

from ftdata.questions import load_questions

EVAL_SET = (Path(__file__).resolve().parents[3]
            / "packages" / "eval" / "eval_set.jsonl")


def _eval_questions():
    import json
    return {json.loads(l)["question"]
            for l in EVAL_SET.read_text(encoding="utf-8").splitlines() if l.strip()}


def test_pool_loads_nonempty():
    qs = load_questions()
    assert len(qs) >= 30


def test_questions_unique():
    qs = load_questions()
    assert len(qs) == len(set(qs))


def test_pool_disjoint_from_eval_set():
    # ⚠️ train/eval 오염 금지: 질문 풀과 평가셋이 하나도 겹치면 안 된다
    pool = set(load_questions())
    overlap = pool & _eval_questions()
    assert overlap == set(), overlap
```

- [ ] **Step 3: 실패 → 구현 → 통과**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_questions.py -v`
Expected: PASS (3 passed). 특히 `test_pool_disjoint_from_eval_set`가 통과해야 함(겹침 0).
> 만약 disjoint 테스트가 실패하면(겹치는 질문 존재), 겹치는 질문을 다른 표현/소주제로 교체해 disjoint를 만든다.

- [ ] **Step 4: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/ftdata/question_pool.jsonl packages/ftdata/src/ftdata/questions.py packages/ftdata/tests/test_questions.py
git commit -m "feat(ftdata): add eval-disjoint question pool (30) + loader"
```

---

## Task 2: 형식 필터 (eval 지표 재사용)

**Files:**
- Create: `packages/ftdata/src/ftdata/filter.py`
- Test: `packages/ftdata/tests/test_filter.py`

학습 데이터로 채택할 후보는 **상담형 구조·`[n]` 인용·면책·출처를 모두** 갖춰야 한다. 평가의 `answer_metrics`를 그대로 필터로 재사용(평가=학습 데이터 품질 기준 일치).

- [ ] **Step 1: 실패하는 테스트** — `packages/ftdata/tests/test_filter.py`:
```python
from ftdata.filter import format_ok


def test_accepts_well_formed_answer():
    answer = ("① 상황 요약: ...\n② 적용 법리: 우선변제 받습니다[1].\n③ 다음 절차: ...\n\n"
              "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    assert format_ok(answer, sources=[{"n": 1}]) is True


def test_rejects_missing_citation():
    answer = ("① ② ③ 구조는 있지만 인용이 없습니다.\n"
              "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    assert format_ok(answer, sources=[]) is False


def test_rejects_missing_structure():
    answer = "우선변제 받습니다[1]. ※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다."
    assert format_ok(answer, sources=[{"n": 1}]) is False


def test_rejects_no_sources():
    answer = ("① ② ③ 우선변제[1].\n※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    assert format_ok(answer, sources=[]) is False
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_filter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ftdata.filter'`

- [ ] **Step 3: 구현** — `packages/ftdata/src/ftdata/filter.py`:
```python
"""학습 후보 형식 필터 — 평가의 answer_metrics를 재사용해 품질 기준을 일치시킨다."""
from eval.answer_metrics import answer_metrics


def format_ok(answer: str, *, sources: list) -> bool:
    """상담형 구조·[n] 인용·면책·출처를 모두 갖춘 후보만 통과."""
    m = answer_metrics(answer, sources=sources, must_mention=[])
    return (m["has_citation"] and m["has_structure"]
            and m["has_disclaimer"] and m["has_sources"])
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_filter.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/ftdata/src/ftdata/filter.py packages/ftdata/tests/test_filter.py
git commit -m "feat(ftdata): add format filter reusing eval metrics"
```

---

## Task 3: chat-example 빌더 + train/valid 분할

**Files:**
- Create: `packages/ftdata/src/ftdata/builder.py`
- Test: `packages/ftdata/tests/test_builder.py`

채택된 (질문, 근거, 답변)을 **서빙과 동일한 입력 형식**(`build_messages`: system+user(근거))에 assistant(답변)를 붙여 MLX chat 예제로 만들고, 결정적으로 train/valid를 분할해 jsonl로 쓴다.

- [ ] **Step 1: 실패하는 테스트** — `packages/ftdata/tests/test_builder.py`:
```python
import json

from ftdata.builder import to_chat_example, split_train_valid, write_jsonl
from rag.types import Retrieved


def _hit(ref):
    return Retrieved(id="i", text=f"근거 {ref}", similarity=0.7, source_type="법령",
                     title=f"주택임대차보호법 {ref}", ref=ref, url="u", date="2023")


def test_to_chat_example_has_system_user_assistant():
    ex = to_chat_example("보증금?", [_hit("제3조의2")], "① ② ③ 우선변제[1]. ※ ... 법률 자문이 아닙니다.")
    roles = [m["role"] for m in ex["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert "근거" in ex["messages"][1]["content"]          # user에 근거 블록
    assert "보증금?" in ex["messages"][1]["content"]        # 질문 포함
    assert ex["messages"][2]["content"].startswith("①")    # assistant = 답변


def test_split_train_valid_deterministic():
    examples = [{"messages": [{"role": "user", "content": str(i)}]} for i in range(10)]
    train, valid = split_train_valid(examples, valid_every=5)
    # 5번째, 10번째(1-indexed)가 valid
    assert len(valid) == 2 and len(train) == 8
    assert valid[0]["messages"][0]["content"] == "4"      # index 4 (5th)


def test_write_jsonl_roundtrip(tmp_path):
    rows = [{"messages": [{"role": "user", "content": "a"}]},
            {"messages": [{"role": "user", "content": "b"}]}]
    p = tmp_path / "train.jsonl"
    write_jsonl(p, rows)
    back = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    assert back == rows
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_builder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ftdata.builder'`

- [ ] **Step 3: 구현** — `packages/ftdata/src/ftdata/builder.py`:
```python
"""채택 후보 → MLX chat JSONL 예제 + train/valid 분할."""
import json
from pathlib import Path

from rag.prompt import build_messages
from rag.types import Retrieved


def to_chat_example(question: str, hits: list[Retrieved], answer: str) -> dict:
    """서빙과 동일한 입력(system+user(근거))에 정답 답변을 붙인 MLX chat 예제."""
    messages = build_messages(question, hits)
    messages.append({"role": "assistant", "content": answer})
    return {"messages": messages}


def split_train_valid(examples: list[dict], valid_every: int = 10):
    """결정적 분할: 1-indexed로 valid_every의 배수번째를 valid로."""
    train, valid = [], []
    for i, ex in enumerate(examples):
        (valid if (i + 1) % valid_every == 0 else train).append(ex)
    return train, valid


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_builder.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/ftdata/src/ftdata/builder.py packages/ftdata/tests/test_builder.py
git commit -m "feat(ftdata): add chat-example builder + deterministic split"
```

---

## Task 4: 후보 생성기

**Files:**
- Create: `packages/ftdata/src/ftdata/generate.py`
- Test: `packages/ftdata/tests/test_generate.py`

질문마다 검색 근거를 한 번 잡고, `run_chat`(서빙과 동일)으로 K개 후보를 temp 다양성으로 생성하며 각 후보의 근거 점수를 매긴다. retriever·llm·judge_fn 주입.

- [ ] **Step 1: 실패하는 테스트** — `packages/ftdata/tests/test_generate.py`:
```python
from ftdata.generate import generate_candidates, Candidate
from rag.types import Retrieved


class StubRetriever:
    def retrieve(self, q):
        return [Retrieved(id="i1", text="임차인은 보증금을 우선변제 받는다", similarity=0.7,
                          source_type="법령", title="주택임대차보호법 제3조의2",
                          ref="제3조의2", url="u", date="2023")]
    def is_grounded(self, hits):
        return True


class FakeLLM:
    def __init__(self, text): self._text = text
    def stream(self, messages, **kw):
        yield self._text


def test_generate_returns_k_candidates_with_hits():
    retr = StubRetriever()
    llm = FakeLLM("① ② ③ 우선변제[1]. ※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    hits, cands = generate_candidates("보증금?", retriever=retr, llm=llm,
                                      judge_fn=lambda p: "0.8", k=3, temperature=0.7)
    assert len(hits) == 1
    assert len(cands) == 3
    c = cands[0]
    assert isinstance(c, Candidate)
    assert "우선변제" in c.answer
    assert c.sources and c.sources[0]["url"] == "u"
    assert c.grounded == 0.8
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ftdata.generate'`

- [ ] **Step 3: 구현** — `packages/ftdata/src/ftdata/generate.py`:
```python
"""질문 → 검색 근거 + run_chat로 K개 후보 답변 생성(temp 다양성) + 근거 점수."""
from dataclasses import dataclass
from typing import Callable

from api.pipeline import run_chat
from eval.judge import groundedness_score
from rag.types import Retrieved


@dataclass
class Candidate:
    answer: str
    sources: list
    grounded: float


def generate_candidates(question: str, *, retriever, llm,
                        judge_fn: Callable[[str], str], k: int = 6,
                        temperature: float = 0.7) -> tuple[list[Retrieved], list[Candidate]]:
    hits = retriever.retrieve(question)
    contexts = [h.text for h in hits]
    cands: list[Candidate] = []
    for _ in range(k):
        events = list(run_chat(question, retriever=retriever, llm=llm,
                               temperature=temperature))
        done = next(e for e in events if e["type"] == "done")
        grounded = groundedness_score(question=question, answer=done["answer"],
                                      contexts=contexts, judge_fn=judge_fn)
        cands.append(Candidate(answer=done["answer"], sources=done["sources"],
                               grounded=grounded))
    return hits, cands
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest tests/test_generate.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 전체 ftdata 빠른 테스트**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest -m "not slow" -q`
Expected: 모든 단위 테스트 통과.

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/ftdata/src/ftdata/generate.py packages/ftdata/tests/test_generate.py
git commit -m "feat(ftdata): add candidate generator (reuses run_chat)"
```

---

## Task 5: 빌드 CLI

**Files:**
- Create: `packages/ftdata/src/ftdata/cli.py`
- (테스트 없음 — 라이브 오케스트레이션. 순수 로직은 Task 2~4에서 검증됨)

- [ ] **Step 1: 구현** — `packages/ftdata/src/ftdata/cli.py`:
```python
"""라이브 FT 데이터 빌드: 질문 풀 → 후보 생성 → 형식·근거 필터 → MLX chat JSONL.

실행: uv run --package ftdata python -m ftdata.cli [--k 6] [--per-q 2] [--min-ground 0.5]
출력: data/ft/train.jsonl, data/ft/valid.jsonl, data/ft/stats.json
"""
import json
import sys
from pathlib import Path

from api.llm import MlxLLM
from api.settings import Settings
from rag.retriever import Retriever

from .builder import split_train_valid, to_chat_example, write_jsonl
from .filter import format_ok
from .generate import generate_candidates
from .questions import load_questions

_REPO_ROOT = Path(__file__).resolve().parents[4]
_OUT_DIR = _REPO_ROOT / "data" / "ft"


def _arg(name: str, default):
    if name in sys.argv:
        return type(default)(sys.argv[sys.argv.index(name) + 1])
    return default


def main() -> None:
    k = _arg("--k", 6)
    per_q = _arg("--per-q", 2)          # 질문당 채택할 최대 후보 수(근거 점수 상위)
    min_ground = _arg("--min-ground", 0.5)

    settings = Settings.from_env()
    retriever = Retriever(settings.rag)
    llm = MlxLLM(settings.mlx_model)
    judge_fn = lambda prompt: "".join(llm.stream(
        [{"role": "user", "content": prompt}], max_tokens=16, temperature=0.0))

    questions = load_questions()
    examples: list[dict] = []
    n_cand = n_pass = 0
    for i, q in enumerate(questions, 1):
        hits, cands = generate_candidates(q, retriever=retriever, llm=llm,
                                          judge_fn=judge_fn, k=k, temperature=0.7)
        n_cand += len(cands)
        kept = [c for c in cands if format_ok(c.answer, sources=c.sources)
                and c.grounded >= min_ground]
        kept.sort(key=lambda c: c.grounded, reverse=True)
        kept = kept[:per_q]
        n_pass += len(kept)
        for c in kept:
            examples.append(to_chat_example(q, hits, c.answer))
        print(f"[{i}/{len(questions)}] kept {len(kept)}/{len(cands)} (총 {len(examples)})")

    train, valid = split_train_valid(examples, valid_every=10)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(_OUT_DIR / "train.jsonl", train)
    write_jsonl(_OUT_DIR / "valid.jsonl", valid)
    stats = {"questions": len(questions), "candidates": n_cand, "kept": n_pass,
             "pass_rate": (n_pass / n_cand if n_cand else 0.0),
             "train": len(train), "valid": len(valid),
             "k": k, "per_q": per_q, "min_ground": min_ground}
    (_OUT_DIR / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print("\n=== 빌드 요약 ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"저장: {_OUT_DIR}/train.jsonl, valid.jsonl, stats.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: import-without-model 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package ftdata python -c "import ftdata.cli, sys; print('cli ok; mlx loaded:', 'mlx' in sys.modules)"`
Expected: `cli ok; mlx loaded: False` (MlxLLM은 main() 안에서만 생성 → import 시 모델 로딩 없음).

- [ ] **Step 3: 전체 ftdata 빠른 테스트 (회귀 확인)**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/ftdata && uv run pytest -m "not slow" -q`
Expected: 통과.

- [ ] **Step 4: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/ftdata/src/ftdata/cli.py
git commit -m "feat(ftdata): add live FT dataset build CLI"
```

---

## Task 6: 라이브 데이터셋 빌드 + 검수

**Files:** 없음(빌드 실행). 출력 `data/ft/*`(gitignore). 통계는 `docs/superpowers/notes/`에 커밋.

- [ ] **Step 1: 라이브 빌드 (30문항 × K 후보 생성, 수 분~십수 분)**
Run:
```bash
cd /Users/fujii0711/Claude/privateLLM
uv run --package ftdata python -m ftdata.cli --k 6 --per-q 2 --min-ground 0.5
```
Expected: 질문별 진행 로그 후 요약(`questions/candidates/kept/pass_rate/train/valid`) + `data/ft/train.jsonl`·`valid.jsonl`·`stats.json` 저장.

- [ ] **Step 2: 데이터 품질 검수 (사람 확인)**
무작위 3~5개 예제를 출력해 학습 타깃 품질을 확인:
```bash
cd /Users/fujii0711/Claude/privateLLM && uv run --package ftdata python -c "
import json, pathlib
rows = [json.loads(l) for l in pathlib.Path('data/ft/train.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
print('train 예제 수:', len(rows))
for ex in rows[:3]:
    a = ex['messages'][-1]['content']
    print('--- assistant ---'); print(a[:400]); print()
"
```
확인 항목(보고): assistant 답변이 ①②③ 구조 + `[n]` 인용 + 면책을 갖췄는가? 근거에 부합하는가(환각 없는가)? user 메시지에 근거 블록이 포함됐는가? **train/valid에 평가셋 질문이 없는가**(질문 풀 disjoint 보장됨 — 재확인).

- [ ] **Step 3: 빌드 통계 문서 커밋 (숫자만)**
```bash
cd /Users/fujii0711/Claude/privateLLM
mkdir -p docs/superpowers/notes
uv run --package ftdata python -c "
import json, pathlib
s = json.loads(pathlib.Path('data/ft/stats.json').read_text(encoding='utf-8'))
pathlib.Path('docs/superpowers/notes/ft-dataset-stats.md').write_text(
    '# FT 데이터셋 빌드 통계 (rejection-sampling distillation)\n\n'
    '질문 풀: packages/ftdata/question_pool.jsonl (평가셋과 disjoint)\n'
    'teacher: base Qwen2.5-7B-4bit, temp 0.7, 형식+근거 필터\n\n'
    '```json\n' + json.dumps(s, ensure_ascii=False, indent=2) + '\n```\n\n'
    'Plan 3C에서 이 train/valid로 QLoRA 어댑터를 학습한다.\n', encoding='utf-8')
print('기록됨')
"
git add docs/superpowers/notes/ft-dataset-stats.md
git commit -m "docs(ftdata): record FT dataset build stats"
```

> **품질이 낮거나(통과율 매우 낮음) 양이 부족하면:** `--k`를 늘리거나(후보 다양성↑), `--per-q`를 늘리거나(질문당 채택↑), 질문 풀을 확장한다. teacher를 더 강한 모델(예: Qwen2.5-32B-4bit, 48GB에 적재 가능)로 바꾸면 타깃 품질이 오른다 — Plan 3C 전 선택적 개선.

---

## 완료 기준 (Definition of Done)

- [ ] `cd packages/ftdata && uv run pytest -m "not slow"` 전체 통과(questions 3, filter 4, builder 3, generate 1).
- [ ] `test_pool_disjoint_from_eval_set` 통과(질문 풀이 평가셋과 겹치지 않음 — 오염 방지).
- [ ] `uv run --package ftdata python -m ftdata.cli`가 `data/ft/train.jsonl`·`valid.jsonl`·`stats.json` 산출.
- [ ] train 예제들이 ①②③ 구조 + `[n]` 인용 + 면책을 갖춘 MLX chat 형식(검수 확인).
- [ ] 빌드 통계가 `docs/superpowers/notes/ft-dataset-stats.md`에 기록됨.

이 시점에서 **QLoRA 학습 가능한 chat JSONL 데이터셋**이 완성된다 → Plan 3C의 입력.

---

## 후속 계획으로의 인계 (Plan 3C)

- **학습:** `mlx_lm.convert`로 베이스 4bit 변환은 이미 캐시된 모델 사용 가능. `mlx_lm.lora --train --data data/ft --iters ... --batch-size ...`로 어댑터 학습(`data/ft`에 train.jsonl/valid.jsonl 존재). chat 형식(`{"messages":[...]}`)은 mlx-lm가 지원.
- **서빙:** `api/llm.py`의 `MlxLLM`에 어댑터 경로를 받는 변형(`MlxLLM(model_name, adapter_path=...)`) 추가 — `mlx_lm.load(model, adapter_path=...)`.
- **A/B:** `eval.cli --label qlora`로 동일 평가셋(16문항) 재측정 → `baseline.json`(structure 0.75/groundedness 0.69/...)과 비교. 검색은 동일하므로 recall 불변(검증 포인트), 형식·충실도 상승이 QLoRA 기여.
- **데이터 한계:** 자기-distillation이라 타깃 상한이 base 모델 능력. 형식 일관성(structure_rate) 개선엔 효과적이나 새 지식은 추가 안 됨. 더 큰 teacher나 실제 생활법령/상담사례(`해설`/`상담사례` source_type) 보강은 후속 개선.
