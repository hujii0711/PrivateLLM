# 계획 3A — 평가 하니스 + 베이스라인 측정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 주택임대차 보증금 반환 RAG 챗봇의 품질을 정량 측정하는 평가 하니스를 만들고, 현재 RAG 베이스라인(파인튜닝 없음)의 점수를 산출한다. 이 점수가 Plan 3C에서 QLoRA 어댑터와 A/B 비교할 기준선이 된다.

**Architecture:** uv 워크스페이스에 `packages/eval` 추가. `apps/api`의 `run_chat`(서빙과 동일 코드 → 평가 일관성)과 `packages/rag`의 retriever를 재사용한다. 지표는 ① **검색 recall@k**(기대 법조항이 top-k에 검색됐는가, 결정적) ② **답변 형식**(인용 `[n]`·상담형 구조·면책·출처 유무, 결정적) ③ **키워드 충실도**(기대 키워드 포함, 결정적) ④ **LLM-as-judge 충실도/말투**(주입 가능, 선택). retriever·llm·judge는 주입 가능하게 해 모델 없이 단위 테스트한다.

**Tech Stack:** Python 3.11, uv(workspace), pytest. 라이브 실행 시 `apps/api`의 MlxLLM(Qwen2.5-7B) + `data/chroma`(Plan 1 인덱스) + bge-m3.

**Scope (YAGNI):** 이 계획은 **평가 하니스 + 베이스라인 측정만**. FT 데이터 수집·QLoRA 학습·A/B는 Plan 3B/3C. 평가셋은 보증금 반환 중심 ~16문항(연구 PoC 규모; 확장 가능). LLM-as-judge는 결정적 지표를 보완하는 부차 지표(같은 base 모델을 judge로 쓰는 한계는 A/B에서 동일 judge로 상대 비교하므로 허용).

**전제:** Plan 1·2A 완료. `data/chroma`에 `jeonse_deposit`(1264 청크) 존재. Qwen2.5-7B-4bit HF 캐시됨.

---

## File Structure

```
packages/eval/
├── pyproject.toml                 # eval 패키지 (rag + api workspace 의존)
├── src/eval/
│   ├── __init__.py
│   ├── dataset.py                 # EvalItem 스키마 + jsonl 로더
│   ├── retrieval_metrics.py       # recall@k / hit@k (결정적)
│   ├── answer_metrics.py          # 형식·키워드 지표 (결정적)
│   ├── judge.py                   # LLM-as-judge (주입 가능)
│   ├── runner.py                  # 평가셋 → run_chat → per-item 결과
│   ├── report.py                  # 집계 → 요약 지표
│   └── cli.py                     # 라이브 실행 엔트리
├── eval_set.jsonl                 # 큐레이션된 평가셋(그라운드 트루스, 커밋됨)
└── tests/
    ├── conftest.py
    ├── test_dataset.py
    ├── test_retrieval_metrics.py
    ├── test_answer_metrics.py
    ├── test_judge.py
    ├── test_runner.py
    └── test_report.py
```

평가 **실행 결과**(리포트)는 gitignore된 `data/eval_runs/`에 저장(그라운드 트루스인 `eval_set.jsonl`은 패키지에 커밋).

---

## Task 0: packages/eval 스캐폴딩

**Files:**
- Create: `packages/eval/pyproject.toml`
- Create: `packages/eval/src/eval/__init__.py` (빈 파일)
- Create: `packages/eval/tests/conftest.py` (빈 파일)

- [ ] **Step 1: pyproject** — `packages/eval/pyproject.toml`:
```toml
[project]
name = "eval"
version = "0.1.0"
description = "주택임대차 보증금 반환 챗봇 — 평가 하니스"
requires-python = ">=3.11"
dependencies = [
    "rag",
    "api",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.uv.sources]
rag = { workspace = true }
api = { workspace = true }

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["slow: 실제 모델/인덱스를 쓰는 느린 테스트"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/eval"]
```

- [ ] **Step 2: 빈 파일 생성**
`packages/eval/src/eval/__init__.py` (빈), `packages/eval/tests/conftest.py` (빈).

- [ ] **Step 3: 워크스페이스 동기화**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv sync`
Expected: `eval` 패키지 인식, rag·api 워크스페이스 의존 해결. 에러 없음.
> 루트 `pyproject.toml`의 `members`는 `packages/*`를 포함하므로 자동 편입. `apps/web`은 `exclude`되어 있어 영향 없음.

- [ ] **Step 4: pytest 수집 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest -q`
Expected: `no tests ran` (에러 없음).

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git checkout -b plan3a-eval
git add packages/eval pyproject.toml uv.lock
git commit -m "chore(eval): scaffold eval package"
```

---

## Task 1: EvalItem 스키마 + 로더

**Files:**
- Create: `packages/eval/src/eval/dataset.py`
- Test: `packages/eval/tests/test_dataset.py`

- [ ] **Step 1: 실패하는 테스트** — `packages/eval/tests/test_dataset.py`:
```python
from eval.dataset import EvalItem, load_eval_set


def test_eval_item_fields():
    it = EvalItem(id="q1", question="보증금 못 받았어요",
                  expected_refs=["제3조의2"], must_mention=["우선변제"])
    assert it.id == "q1"
    assert it.expected_refs == ["제3조의2"]


def test_load_eval_set(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text(
        '{"id":"q1","question":"보증금?","expected_refs":["제3조의2"],"must_mention":["우선변제"]}\n'
        '{"id":"q2","question":"기간?","expected_refs":["제4조"],"must_mention":[]}\n',
        encoding="utf-8",
    )
    items = load_eval_set(p)
    assert len(items) == 2
    assert items[0].id == "q1" and items[1].expected_refs == ["제4조"]


def test_load_skips_blank_lines(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('{"id":"q1","question":"x","expected_refs":[],"must_mention":[]}\n\n',
                 encoding="utf-8")
    assert len(load_eval_set(p)) == 1
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_dataset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.dataset'`

- [ ] **Step 3: 구현** — `packages/eval/src/eval/dataset.py`:
```python
"""평가셋 항목 스키마 + jsonl 로더."""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalItem:
    id: str
    question: str
    expected_refs: list[str] = field(default_factory=list)   # 기대 법조항 ref (예: "제3조의2")
    must_mention: list[str] = field(default_factory=list)    # 답변에 포함돼야 할 키워드


def load_eval_set(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        items.append(EvalItem(
            id=d["id"], question=d["question"],
            expected_refs=d.get("expected_refs", []),
            must_mention=d.get("must_mention", []),
        ))
    return items
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_dataset.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/dataset.py packages/eval/tests/test_dataset.py
git commit -m "feat(eval): add EvalItem schema + loader"
```

---

## Task 2: 큐레이션된 평가셋 (그라운드 트루스)

**Files:**
- Create: `packages/eval/eval_set.jsonl`
- Test: `packages/eval/tests/test_eval_set_valid.py`

주택임대차보호법 보증금 반환 관련 대표 질문 16문항. `expected_refs`는 Plan 1이 색인한 실제 조문 ref(주임법 조문번호)와 일치해야 한다.

- [ ] **Step 1: 평가셋 작성** — `packages/eval/eval_set.jsonl` (한 줄에 한 항목):
```json
{"id":"q01","question":"전세 보증금을 집주인이 안 돌려줘요. 어떻게 해야 하나요?","expected_refs":["제3조의2","제3조의3"],"must_mention":["임차권등기","보증금"]}
{"id":"q02","question":"이사를 가야 하는데 보증금을 못 받았습니다. 임차권등기명령을 신청할 수 있나요?","expected_refs":["제3조의3"],"must_mention":["임차권등기명령"]}
{"id":"q03","question":"확정일자를 받으면 어떤 효력이 생기나요?","expected_refs":["제3조의2"],"must_mention":["우선변제"]}
{"id":"q04","question":"보증금을 우선변제 받으려면 어떤 요건을 갖춰야 하나요?","expected_refs":["제3조","제3조의2"],"must_mention":["대항요건","확정일자"]}
{"id":"q05","question":"살던 집이 경매에 넘어갔는데 소액 임차인은 보증금을 먼저 받을 수 있나요?","expected_refs":["제8조"],"must_mention":["우선변제","소액"]}
{"id":"q06","question":"임대차 기간을 따로 정하지 않으면 계약 기간은 몇 년인가요?","expected_refs":["제4조"],"must_mention":["2년"]}
{"id":"q07","question":"계약갱신요구권은 어떻게 행사하나요?","expected_refs":["제6조의3"],"must_mention":["갱신"]}
{"id":"q08","question":"묵시적으로 갱신된 뒤에 중간에 나가고 싶으면 어떻게 하나요?","expected_refs":["제6조의2"],"must_mention":["해지"]}
{"id":"q09","question":"집주인이 보증금을 5% 넘게 올려달라고 합니다. 가능한가요?","expected_refs":["제7조"],"must_mention":["증액","5"]}
{"id":"q10","question":"대항력은 언제 생기나요?","expected_refs":["제3조"],"must_mention":["인도","주민등록"]}
{"id":"q11","question":"보증금을 돌려받기 전에 이사를 가도 대항력이 유지되나요?","expected_refs":["제3조의3"],"must_mention":["임차권등기"]}
{"id":"q12","question":"임대차가 끝났는데 집주인이 보증금 반환을 미룹니다. 소송 말고 방법이 있나요?","expected_refs":["제3조의2","제3조의3"],"must_mention":["임차권등기"]}
{"id":"q13","question":"보증금 반환과 집을 비워주는 것 중 무엇을 먼저 해야 하나요?","expected_refs":["제3조의2"],"must_mention":["동시이행"]}
{"id":"q14","question":"확정일자와 전입신고는 어떻게 다른가요?","expected_refs":["제3조","제3조의2"],"must_mention":["대항","우선변제"]}
{"id":"q15","question":"임차권등기명령을 신청하면 비용은 누가 부담하나요?","expected_refs":["제3조의3"],"must_mention":["임차권등기"]}
{"id":"q16","question":"소액임차인 최우선변제 금액은 어떻게 정해지나요?","expected_refs":["제8조"],"must_mention":["최우선변제","일정액"]}
```

- [ ] **Step 2: 평가셋 유효성 테스트** — `packages/eval/tests/test_eval_set_valid.py`:
```python
from pathlib import Path

from eval.dataset import load_eval_set

EVAL_SET = Path(__file__).resolve().parents[1] / "eval_set.jsonl"


def test_eval_set_loads_and_is_nonempty():
    items = load_eval_set(EVAL_SET)
    assert len(items) >= 16


def test_every_item_has_question_and_unique_id():
    items = load_eval_set(EVAL_SET)
    ids = [it.id for it in items]
    assert len(ids) == len(set(ids))                 # id 유일
    assert all(it.question.strip() for it in items)  # 질문 비어있지 않음


def test_expected_refs_look_like_article_numbers():
    items = load_eval_set(EVAL_SET)
    for it in items:
        for ref in it.expected_refs:
            assert ref.startswith("제") and "조" in ref, (it.id, ref)
```

- [ ] **Step 3: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_eval_set_valid.py -v`
Expected: PASS (3 passed)

- [ ] **Step 4: (라이브 권장) 기대 조문이 실제로 인덱스에 존재하는지 확인** — 평가셋 품질 점검. 이 단계는 `data/chroma`가 있어야 하며 결과만 확인(테스트 아님):
```bash
cd /Users/fujii0711/Claude/privateLLM && uv run --package eval python -c "
import chromadb, json, pathlib
from rag.config import RagConfig
cfg = RagConfig()
col = chromadb.PersistentClient(path=str(cfg.chroma_dir)).get_collection(cfg.collection)
got = col.get(where={'source_type':'법령'}, include=['metadatas'])
refs = {m['ref'] for m in got['metadatas'] if '주택임대차보호법' in m['title']}
items = [json.loads(l) for l in pathlib.Path('packages/eval/eval_set.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()]
expected = {r for it in items for r in it['expected_refs']}
missing = expected - refs
print('기대 조문 중 인덱스에 없는 것:', missing or '없음(모두 존재)')
"
```
Expected: `없음(모두 존재)`. 누락 ref가 있으면 해당 조문이 주임법에 실제 존재하는지 확인하고 평가셋의 ref를 인덱스의 실제 ref로 교정(테스트는 유지).

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/eval_set.jsonl packages/eval/tests/test_eval_set_valid.py
git commit -m "feat(eval): add curated 보증금 반환 eval set (16 items)"
```

---

## Task 3: 검색 지표 (recall@k / hit@k)

**Files:**
- Create: `packages/eval/src/eval/retrieval_metrics.py`
- Test: `packages/eval/tests/test_retrieval_metrics.py`

- [ ] **Step 1: 실패하는 테스트** — `packages/eval/tests/test_retrieval_metrics.py`:
```python
from eval.retrieval_metrics import ref_hit, recall_at_k


def test_ref_hit_true_when_expected_ref_retrieved():
    assert ref_hit(retrieved_refs=["제3조의2", "제4조"], expected_refs=["제3조의2"]) is True


def test_ref_hit_false_when_none_retrieved():
    assert ref_hit(retrieved_refs=["제4조"], expected_refs=["제3조의2"]) is False


def test_ref_hit_true_if_any_expected_present():
    # 기대 ref 중 하나라도 검색되면 hit
    assert ref_hit(retrieved_refs=["제3조의3"], expected_refs=["제3조의2", "제3조의3"]) is True


def test_ref_hit_with_no_expected_refs_is_true():
    # 기대 조문이 없는 항목은 검색 평가에서 제외(hit=True로 무시)
    assert ref_hit(retrieved_refs=["제4조"], expected_refs=[]) is True


def test_recall_at_k_is_mean_hit_rate():
    # 3개 항목 중 2개 hit → 2/3
    per_item = [True, False, True]
    assert recall_at_k(per_item) == 2 / 3
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_retrieval_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.retrieval_metrics'`

- [ ] **Step 3: 구현** — `packages/eval/src/eval/retrieval_metrics.py`:
```python
"""검색 품질 지표: 기대 법조항이 top-k에 검색됐는가."""


def ref_hit(*, retrieved_refs: list[str], expected_refs: list[str]) -> bool:
    """기대 ref가 하나도 없으면 평가 제외(True). 있으면 그 중 하나라도 검색되면 True."""
    if not expected_refs:
        return True
    retrieved = set(retrieved_refs)
    return any(r in retrieved for r in expected_refs)


def recall_at_k(per_item_hits: list[bool]) -> float:
    """항목별 hit 불리언 리스트 → 평균 hit율."""
    if not per_item_hits:
        return 0.0
    return sum(1 for h in per_item_hits if h) / len(per_item_hits)
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_retrieval_metrics.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/retrieval_metrics.py packages/eval/tests/test_retrieval_metrics.py
git commit -m "feat(eval): add retrieval recall@k metric"
```

---

## Task 4: 답변 형식·키워드 지표

**Files:**
- Create: `packages/eval/src/eval/answer_metrics.py`
- Test: `packages/eval/tests/test_answer_metrics.py`

베이스라인 연구 가설(인용·구조·면책·키워드 준수율)을 결정적으로 측정한다.

- [ ] **Step 1: 실패하는 테스트** — `packages/eval/tests/test_answer_metrics.py`:
```python
from eval.answer_metrics import answer_metrics


def test_detects_citation_structure_disclaimer():
    answer = ("① 상황 요약: ...\n② 적용 법리: 우선변제 받습니다[1].\n③ 다음 절차: ...\n\n"
              "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    m = answer_metrics(answer, sources=[{"n": 1}], must_mention=["우선변제"])
    assert m["has_citation"] is True
    assert m["has_structure"] is True
    assert m["has_disclaimer"] is True
    assert m["has_sources"] is True
    assert m["mention_coverage"] == 1.0


def test_missing_signals():
    m = answer_metrics("그냥 평범한 답변입니다.", sources=[], must_mention=["우선변제", "확정일자"])
    assert m["has_citation"] is False
    assert m["has_structure"] is False
    assert m["has_disclaimer"] is False
    assert m["has_sources"] is False
    assert m["mention_coverage"] == 0.0


def test_partial_mention_coverage():
    m = answer_metrics("확정일자가 중요합니다[1].", sources=[{"n": 1}],
                       must_mention=["우선변제", "확정일자"])
    assert m["mention_coverage"] == 0.5    # 2개 중 1개 포함


def test_mention_coverage_is_one_when_no_keywords():
    m = answer_metrics("아무 답변[1].", sources=[{"n": 1}], must_mention=[])
    assert m["mention_coverage"] == 1.0
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_answer_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.answer_metrics'`

- [ ] **Step 3: 구현** — `packages/eval/src/eval/answer_metrics.py`:
```python
"""답변의 형식·키워드 준수 지표(결정적)."""
import re

_CITE = re.compile(r"\[\d+\]")
_STRUCT = ("①", "②", "③")
_DISCLAIMER = "법률 자문이 아닙니다"


def answer_metrics(answer: str, *, sources: list, must_mention: list[str]) -> dict:
    has_citation = bool(_CITE.search(answer))
    has_structure = all(mark in answer for mark in _STRUCT)
    has_disclaimer = _DISCLAIMER in answer
    has_sources = len(sources) > 0
    if must_mention:
        hit = sum(1 for kw in must_mention if kw in answer)
        coverage = hit / len(must_mention)
    else:
        coverage = 1.0
    return {
        "has_citation": has_citation,
        "has_structure": has_structure,
        "has_disclaimer": has_disclaimer,
        "has_sources": has_sources,
        "mention_coverage": coverage,
    }
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_answer_metrics.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/answer_metrics.py packages/eval/tests/test_answer_metrics.py
git commit -m "feat(eval): add answer format/keyword metrics"
```

---

## Task 5: LLM-as-judge 충실도 (주입 가능)

**Files:**
- Create: `packages/eval/src/eval/judge.py`
- Test: `packages/eval/tests/test_judge.py`

답변이 검색 근거에 기반했는지(groundedness)를 LLM judge로 0~1 점수화. judge 호출은 주입 가능(테스트는 가짜 judge).

- [ ] **Step 1: 실패하는 테스트** — `packages/eval/tests/test_judge.py`:
```python
from eval.judge import groundedness_score, JUDGE_PROMPT_HINT


def test_uses_injected_judge_and_parses_score():
    # 가짜 judge: 항상 "0.8"을 반환
    score = groundedness_score(
        question="보증금?", answer="우선변제 받습니다[1].",
        contexts=["임차인은 보증금을 우선변제 받는다"],
        judge_fn=lambda prompt: "이 답변은 근거에 부합합니다. 점수: 0.8",
    )
    assert score == 0.8


def test_clamps_and_parses_first_number():
    score = groundedness_score(
        question="q", answer="a", contexts=["c"],
        judge_fn=lambda prompt: "1.0",
    )
    assert score == 1.0


def test_returns_zero_when_no_number():
    score = groundedness_score(
        question="q", answer="a", contexts=["c"],
        judge_fn=lambda prompt: "판단 불가",
    )
    assert score == 0.0


def test_judge_prompt_hint_mentions_grounding():
    assert "근거" in JUDGE_PROMPT_HINT
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_judge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.judge'`

- [ ] **Step 3: 구현** — `packages/eval/src/eval/judge.py`:
```python
"""LLM-as-judge: 답변이 검색 근거에 기반했는지 0~1 점수화. judge_fn 주입 가능."""
import re
from typing import Callable

JUDGE_PROMPT_HINT = (
    "아래 '근거'만으로 '답변'의 사실 진술이 뒷받침되는지 0.0~1.0 사이 숫자로만 평가하세요. "
    "근거에 없는 내용을 단정하면 낮게 점수를 줍니다."
)

_NUM = re.compile(r"\d+(?:\.\d+)?")


def build_judge_prompt(question: str, answer: str, contexts: list[str]) -> str:
    ctx = "\n".join(f"- {c}" for c in contexts)
    return (f"{JUDGE_PROMPT_HINT}\n\n[질문]\n{question}\n\n[근거]\n{ctx}\n\n"
            f"[답변]\n{answer}\n\n점수(0.0~1.0):")


def groundedness_score(*, question: str, answer: str, contexts: list[str],
                       judge_fn: Callable[[str], str]) -> float:
    out = judge_fn(build_judge_prompt(question, answer, contexts))
    m = _NUM.search(out)
    if not m:
        return 0.0
    return max(0.0, min(1.0, float(m.group(0))))
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_judge.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/judge.py packages/eval/tests/test_judge.py
git commit -m "feat(eval): add LLM-as-judge groundedness scorer"
```

---

## Task 6: 평가 러너

**Files:**
- Create: `packages/eval/src/eval/runner.py`
- Test: `packages/eval/tests/test_runner.py`

각 평가 항목을 검색 + `run_chat`(서빙과 동일 코드)으로 돌려 항목별 결과를 만든다. retriever·llm·judge_fn 주입.

- [ ] **Step 1: 실패하는 테스트** — `packages/eval/tests/test_runner.py`:
```python
from eval.dataset import EvalItem
from eval.runner import run_item, ItemResult
from rag.types import Retrieved


class StubRetriever:
    def __init__(self, refs):
        self._refs = refs
    def retrieve(self, q):
        return [Retrieved(id=f"i{i}", text=f"근거{r}", similarity=0.7, source_type="법령",
                          title=f"주택임대차보호법 {r}", ref=r, url=f"u{i}", date="2023")
                for i, r in enumerate(self._refs)]
    def is_grounded(self, hits):
        return True


class FakeLLM:
    def __init__(self, text): self._text = text
    def stream(self, messages, **kw):
        yield self._text


def test_run_item_computes_retrieval_and_answer_metrics():
    item = EvalItem(id="q1", question="보증금?", expected_refs=["제3조의2"],
                    must_mention=["우선변제"])
    retr = StubRetriever(["제3조의2", "제4조"])
    llm = FakeLLM("① ② ③ 우선변제 받습니다[1]. ※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    res = run_item(item, retriever=retr, llm=llm, judge_fn=lambda p: "0.9", top_k=6)

    assert isinstance(res, ItemResult)
    assert res.retrieval_hit is True              # 제3조의2 검색됨
    assert res.metrics["has_citation"] is True
    assert res.metrics["has_disclaimer"] is True
    assert res.metrics["mention_coverage"] == 1.0
    assert res.groundedness == 0.9


def test_run_item_retrieval_miss():
    item = EvalItem(id="q2", question="기간?", expected_refs=["제4조"], must_mention=[])
    retr = StubRetriever(["제3조의2"])             # 제4조 없음
    llm = FakeLLM("답변[1].")
    res = run_item(item, retriever=retr, llm=llm, judge_fn=lambda p: "0.5", top_k=6)
    assert res.retrieval_hit is False
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.runner'`

- [ ] **Step 3: 구현** — `packages/eval/src/eval/runner.py`:
```python
"""평가 러너: 평가 항목 → 검색 + run_chat → 지표."""
from dataclasses import dataclass
from typing import Callable

from api.pipeline import run_chat

from .answer_metrics import answer_metrics
from .dataset import EvalItem
from .judge import groundedness_score
from .retrieval_metrics import ref_hit


@dataclass
class ItemResult:
    id: str
    question: str
    answer: str
    retrieval_hit: bool
    metrics: dict
    groundedness: float


def run_item(item: EvalItem, *, retriever, llm,
             judge_fn: Callable[[str], str], top_k: int = 6) -> ItemResult:
    hits = retriever.retrieve(item.question)
    retrieved_refs = [h.ref for h in hits]
    hit = ref_hit(retrieved_refs=retrieved_refs, expected_refs=item.expected_refs)

    events = list(run_chat(item.question, retriever=retriever, llm=llm))
    done = next(e for e in events if e["type"] == "done")
    answer, sources = done["answer"], done["sources"]

    metrics = answer_metrics(answer, sources=sources, must_mention=item.must_mention)
    grounded = groundedness_score(
        question=item.question, answer=answer,
        contexts=[h.text for h in hits], judge_fn=judge_fn,
    )
    return ItemResult(id=item.id, question=item.question, answer=answer,
                      retrieval_hit=hit, metrics=metrics, groundedness=grounded)
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_runner.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/runner.py packages/eval/tests/test_runner.py
git commit -m "feat(eval): add per-item eval runner (reuses run_chat)"
```

---

## Task 7: 리포트 집계 + CLI

**Files:**
- Create: `packages/eval/src/eval/report.py`
- Create: `packages/eval/src/eval/cli.py`
- Test: `packages/eval/tests/test_report.py`

- [ ] **Step 1: 실패하는 테스트** — `packages/eval/tests/test_report.py`:
```python
from eval.report import aggregate
from eval.runner import ItemResult


def _r(hit, cit, disc, cov, ground):
    return ItemResult(id="x", question="q", answer="a", retrieval_hit=hit,
                      metrics={"has_citation": cit, "has_structure": True,
                               "has_disclaimer": disc, "has_sources": cit,
                               "mention_coverage": cov},
                      groundedness=ground)


def test_aggregate_means():
    results = [
        _r(True, True, True, 1.0, 0.9),
        _r(True, False, True, 0.5, 0.7),
        _r(False, True, False, 0.0, 0.5),
    ]
    agg = aggregate(results)
    assert agg["n"] == 3
    assert abs(agg["recall_at_k"] - 2 / 3) < 1e-9
    assert abs(agg["citation_rate"] - 2 / 3) < 1e-9
    assert abs(agg["disclaimer_rate"] - 2 / 3) < 1e-9
    assert abs(agg["mention_coverage"] - 0.5) < 1e-9
    assert abs(agg["groundedness"] - (0.9 + 0.7 + 0.5) / 3) < 1e-9


def test_aggregate_empty():
    agg = aggregate([])
    assert agg["n"] == 0
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.report'`

- [ ] **Step 3: 구현**

`packages/eval/src/eval/report.py`:
```python
"""항목 결과 집계."""
from .runner import ItemResult


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def aggregate(results: list[ItemResult]) -> dict:
    if not results:
        return {"n": 0}
    return {
        "n": len(results),
        "recall_at_k": _mean([1.0 if r.retrieval_hit else 0.0 for r in results]),
        "citation_rate": _mean([1.0 if r.metrics["has_citation"] else 0.0 for r in results]),
        "structure_rate": _mean([1.0 if r.metrics["has_structure"] else 0.0 for r in results]),
        "disclaimer_rate": _mean([1.0 if r.metrics["has_disclaimer"] else 0.0 for r in results]),
        "sources_rate": _mean([1.0 if r.metrics["has_sources"] else 0.0 for r in results]),
        "mention_coverage": _mean([r.metrics["mention_coverage"] for r in results]),
        "groundedness": _mean([r.groundedness for r in results]),
    }
```

`packages/eval/src/eval/cli.py`:
```python
"""라이브 평가 실행: 실제 retriever + MlxLLM로 평가셋을 돌려 리포트를 저장한다.

실행: uv run --package eval python -m eval.cli [--label baseline]
"""
import json
import sys
from pathlib import Path

from api.llm import MlxLLM
from api.settings import Settings
from rag.retriever import Retriever

from .dataset import load_eval_set
from .report import aggregate
from .runner import run_item

_EVAL_SET = Path(__file__).resolve().parents[2] / "eval_set.jsonl"
_REPO_ROOT = Path(__file__).resolve().parents[4]
_OUT_DIR = _REPO_ROOT / "data" / "eval_runs"


def main() -> None:
    label = "baseline"
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]

    settings = Settings.from_env()
    retriever = Retriever(settings.rag)
    llm = MlxLLM(settings.mlx_model)
    judge_fn = lambda prompt: "".join(llm.stream(
        [{"role": "user", "content": prompt}], max_tokens=16, temperature=0.0))

    items = load_eval_set(_EVAL_SET)
    results = []
    for i, item in enumerate(items, 1):
        res = run_item(item, retriever=retriever, llm=llm,
                       judge_fn=judge_fn, top_k=settings.rag.top_k)
        results.append(res)
        print(f"[{i}/{len(items)}] {item.id} hit={res.retrieval_hit} "
              f"cite={res.metrics['has_citation']} ground={res.groundedness:.2f}")

    agg = aggregate(results)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = _OUT_DIR / f"{label}.json"
    out.write_text(json.dumps({
        "label": label, "summary": agg,
        "items": [{"id": r.id, "retrieval_hit": r.retrieval_hit,
                   "metrics": r.metrics, "groundedness": r.groundedness,
                   "answer": r.answer} for r in results],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== {label} 요약 ===")
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest tests/test_report.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 eval 테스트(빠른 것)**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest -m "not slow" -q`
Expected: 모든 eval 단위 테스트 통과.

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/report.py packages/eval/src/eval/cli.py packages/eval/tests/test_report.py
git commit -m "feat(eval): add report aggregation + live eval CLI"
```

---

## Task 8: 라이브 베이스라인 측정

**Files:** 없음(측정 실행). 결과는 `data/eval_runs/baseline.json`(gitignore).

실제 Qwen2.5-7B + 실제 Chroma 인덱스로 평가셋 16문항을 돌려 베이스라인 점수를 산출한다.

- [ ] **Step 1: 라이브 실행 (모델 로딩 + 16문항 생성, 수 분 소요)**
Run:
```bash
cd /Users/fujii0711/Claude/privateLLM
uv run --package eval python -m eval.cli --label baseline
```
Expected: 항목별 진행 로그(`[i/16] qNN hit=... cite=... ground=...`) 후 요약 JSON 출력 + `data/eval_runs/baseline.json` 저장.

- [ ] **Step 2: 결과 해석 + 기록**
요약 지표를 확인하고 보고:
- `recall_at_k`: 검색이 기대 조문을 얼마나 잡았는가 (RAG 검색 품질; 보통 높아야 함)
- `citation_rate` / `structure_rate` / `disclaimer_rate` / `sources_rate`: 베이스라인의 형식 준수율 (← **QLoRA가 개선할 핵심 대상**)
- `mention_coverage`: 기대 키워드 포함률 (충실도 프록시)
- `groundedness`: judge 점수 (부차)

> 이 숫자들이 **Plan 3C의 A/B 기준선**이다. 특히 citation/structure 준수율이 QLoRA로 얼마나 오르는지가 연구의 핵심 결론. `disclaimer_rate`는 파이프라인이 결정적으로 보장하므로 1.0에 가까워야 함(아니면 버그).

- [ ] **Step 3: 베이스라인 요약을 문서로 커밋 (재현용 — 숫자만, 답변 본문 제외)**
`data/eval_runs/baseline.json`은 gitignore이므로, 요약 지표만 `docs/superpowers/notes/`에 기록:
```bash
cd /Users/fujii0711/Claude/privateLLM
mkdir -p docs/superpowers/notes
uv run --package eval python -c "
import json, pathlib
d = json.loads(pathlib.Path('data/eval_runs/baseline.json').read_text(encoding='utf-8'))
pathlib.Path('docs/superpowers/notes/baseline-eval-summary.md').write_text(
    '# 베이스라인 평가 요약 (RAG only, QLoRA 없음)\n\n'
    '평가셋: packages/eval/eval_set.jsonl (16문항)\n\n'
    '```json\n' + json.dumps(d['summary'], ensure_ascii=False, indent=2) + '\n```\n', encoding='utf-8')
print('기록됨')
"
git add docs/superpowers/notes/baseline-eval-summary.md
git commit -m "docs(eval): record RAG baseline scores"
```

---

## 완료 기준 (Definition of Done)

- [ ] `cd packages/eval && uv run pytest -m "not slow"` 전체 통과(dataset 3, eval_set 3, retrieval 5, answer 4, judge 4, runner 2, report 2).
- [ ] `uv run --package eval python -m eval.cli --label baseline`이 16문항을 돌려 요약 지표 + `data/eval_runs/baseline.json` 산출.
- [ ] 베이스라인 요약이 `docs/superpowers/notes/baseline-eval-summary.md`에 기록됨.
- [ ] `disclaimer_rate`가 1.0 근처(결정적 보장 확인). `recall_at_k`·`citation_rate` 등 베이스라인 수치 확보.

이 시점에서 **재현 가능한 평가 도구 + 정량 베이스라인**이 완성된다 → Plan 3C의 A/B 비교 기준.

---

## 후속 계획으로의 인계

- **Plan 3B (FT 데이터):** 생활법령 Q&A·대한법률구조공단 상담사례 수집(Plan 1 `해설`/`상담사례` source_type 채움) → distillation으로 상담형+인용 정답 합성 → MLX chat JSONL. 같은 인덱스에 해설/상담 청크를 추가하면 RAG 코퍼스도 보강됨.
- **Plan 3C (QLoRA + A/B):** `mlx_lm.lora`로 어댑터 학습 → `MlxLLM`에 어댑터 적용 버전 추가 → `eval.cli --label qlora`로 재측정 → baseline.json vs qlora.json 비교. 러너·지표·평가셋을 그대로 재사용(서빙=평가 동일 코드 원칙). 기대: citation_rate·structure_rate·mention_coverage 상승, recall_at_k는 검색 동일이라 불변(검증 포인트).
- 평가셋 확장: 16 → 30~50문항으로 늘리면 통계적 신뢰도 향상(Plan 3C 전에 선택적으로).
