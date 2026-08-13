# 계획 3C — QLoRA 학습 + 어댑터 서빙 + A/B 측정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plan 3B의 학습 데이터(`data/ft/`)로 QLoRA 어댑터를 MLX로 학습하고, 어댑터를 서빙에 적용해 동일 평가셋으로 재측정한 뒤 베이스라인과 **A/B 비교**하여 파인튜닝의 정량적 기여도를 산출한다. **전체 연구의 결론.**

**Architecture:** uv 워크스페이스에 `packages/finetune` 추가(`api`·`eval` 재사용). 학습은 `mlx_lm.lora`(MLX 네이티브 QLoRA) CLI. `api.llm.MlxLLM`에 `adapter_path` 인자 추가(`mlx_lm.load(model, adapter_path=)`). `eval.cli`에 `--adapter` 추가(생성은 어댑터, **judge는 base 유지** → arm 간 judge 일치). 동일 평가셋(16문항, 학습 질문과 disjoint)으로 baseline·qlora를 같은 세션에서 측정 → `finetune.compare`로 델타 산출.

**Tech Stack:** Python 3.11, uv(workspace), pytest. 라이브: mlx_lm.lora(학습) + MlxLLM(어댑터 추론) + Chroma.

**Scope (YAGNI):** 이 계획은 **학습 + A/B만**. 데이터는 Plan 3B 산출물(`data/ft/`) 그대로 사용(없으면 재빌드). 하이퍼파라미터는 소규모(45 train) 형식-LoRA 기준 보수값. teacher 강화·데이터 확장은 범위 밖(필요 시 Plan 3B 재실행).

**전제:** Plan 1·2A·3A·3B 완료. `data/ft/{train,valid}.jsonl` 존재(없으면 `uv run --package ftdata python -m ftdata.cli`로 재생성). Qwen2.5-7B-4bit 캐시됨. mlx-lm 0.31.3.

**핵심 A/B 원칙:** 두 arm(baseline=base, qlora=base+adapter)을 **같은 세션·같은 코드·temp 0.2 동일**로 측정. 검색은 양 arm 동일 → `recall_at_k` 불변(검증 포인트). 결정적 지표(structure/citation/disclaimer/sources/mention)가 A/B의 주 신호; groundedness는 부차(judge는 양 arm 모두 base).

---

## File Structure

```
packages/finetune/
├── pyproject.toml                 # deps: api, eval
├── src/finetune/
│   ├── __init__.py
│   ├── train.py                   # build_lora_command (순수, TDD)
│   ├── compare.py                 # load_summary / compare_runs / to_markdown (순수, TDD)
│   └── compare_cli.py             # baseline.json vs qlora.json → 결론 문서
└── tests/
    ├── conftest.py
    ├── test_train.py
    └── test_compare.py
```

수정(타 패키지 확장):
- `apps/api/src/api/llm.py` — `MlxLLM(__init__)`에 `adapter_path` 추가.
- `packages/eval/src/eval/cli.py` — `--adapter` 인자 + base judge 분리.

산출물(gitignore): `data/adapters/qlora/`(어댑터), `data/eval_runs/{baseline,qlora}.json`. 결론 문서는 `docs/superpowers/notes/`에 커밋.

---

## Task 0: finetune 패키지 스캐폴딩

**Files:**
- Create: `packages/finetune/pyproject.toml`
- Create: `packages/finetune/src/finetune/__init__.py` (빈)
- Create: `packages/finetune/tests/conftest.py` (빈)

- [ ] **Step 1: pyproject** — `packages/finetune/pyproject.toml`:
```toml
[project]
name = "finetune"
version = "0.1.0"
description = "주택임대차 보증금 반환 챗봇 — QLoRA 학습 + A/B"
requires-python = ">=3.11"
dependencies = [
    "api",
    "eval",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.uv.sources]
api = { workspace = true }
eval = { workspace = true }

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["slow: 실제 모델/학습을 쓰는 느린 테스트"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/finetune"]
```

- [ ] **Step 2: 빈 파일** 생성.

- [ ] **Step 3: 동기화 + 수집 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv sync` → finetune 인식, 에러 없음.
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/finetune && uv run pytest -q` → "no tests ran".

- [ ] **Step 4: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git checkout -b plan3c-qlora
git add packages/finetune pyproject.toml uv.lock
git commit -m "chore(finetune): scaffold QLoRA train + A/B package"
```

---

## Task 1: MlxLLM 어댑터 지원

**Files:**
- Modify: `apps/api/src/api/llm.py`
- Test: `apps/api/tests/test_llm_adapter.py`

`MlxLLM(__init__)`에 `adapter_path: str | None = None`를 추가하고 `mlx_lm.load(model_name, adapter_path=adapter_path)`로 로드한다. 기존 동작(어댑터 없음)은 그대로.

- [ ] **Step 1: 현재 llm.py 확인** — `apps/api/src/api/llm.py`의 `MlxLLM.__init__`는 현재:
```python
class MlxLLM:
    def __init__(self, model_name: str = MLX_MODEL):
        from mlx_lm import load
        self._model, self._tokenizer = load(model_name)
```

- [ ] **Step 2: 실패하는 테스트** — `apps/api/tests/test_llm_adapter.py`:
```python
import inspect

from api.llm import MlxLLM


def test_mlxllm_init_accepts_adapter_path():
    params = inspect.signature(MlxLLM.__init__).parameters
    assert "adapter_path" in params
    assert params["adapter_path"].default is None   # 기본은 어댑터 없음(하위호환)
```

- [ ] **Step 3: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/api && uv run pytest tests/test_llm_adapter.py -v`
Expected: FAIL — `assert 'adapter_path' in params`

- [ ] **Step 4: 구현** — `apps/api/src/api/llm.py`의 `MlxLLM`을 수정:
```python
class MlxLLM:
    """mlx-lm 기반 Qwen2.5-7B-Instruct-4bit 스트리밍 추론. adapter_path로 LoRA 어댑터 적용."""
    def __init__(self, model_name: str = MLX_MODEL, adapter_path: str | None = None):
        from mlx_lm import load
        self._model, self._tokenizer = load(model_name, adapter_path=adapter_path)
```
(`stream` 메서드는 변경 없음.)

- [ ] **Step 5: 통과 + 회귀 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/apps/api && uv run pytest tests/test_llm_adapter.py -v && uv run pytest -m "not slow" -q`
Expected: 새 테스트 PASS + 기존 api 빠른 테스트 전부 통과(FakeLLM 등 영향 없음).

- [ ] **Step 6: import-without-model 재확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api python -c "import api.llm, sys; print('mlx loaded:', 'mlx' in sys.modules)"`
Expected: `mlx loaded: False` (지연 import 유지).

- [ ] **Step 7: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/api/src/api/llm.py apps/api/tests/test_llm_adapter.py
git commit -m "feat(api): add adapter_path to MlxLLM (LoRA serving)"
```

---

## Task 2: eval.cli `--adapter` (생성=어댑터, judge=base)

**Files:**
- Modify: `packages/eval/src/eval/cli.py`

A/B의 qlora arm을 위해 생성 LLM에 어댑터를 적용하되, **judge는 base 유지**(arm 간 judge 일치 → 공정 비교). 결정적 지표는 judge와 무관하므로 주 신호는 그대로 비교 가능.

- [ ] **Step 1: 현재 cli.py의 모델 구성부 수정**. 현재(참고):
```python
    settings = Settings.from_env()
    retriever = Retriever(settings.rag)
    llm = MlxLLM(settings.mlx_model)
    judge_fn = lambda prompt: "".join(llm.stream(
        [{"role": "user", "content": prompt}], max_tokens=16, temperature=0.0))
```
이를 다음으로 교체(상단 `import sys`는 이미 있음):
```python
    settings = Settings.from_env()
    retriever = Retriever(settings.rag)

    adapter = (sys.argv[sys.argv.index("--adapter") + 1]
               if "--adapter" in sys.argv else None)
    gen_llm = MlxLLM(settings.mlx_model, adapter_path=adapter)
    # judge는 양 arm 모두 base 모델로 일치시킨다(공정 비교). 어댑터 없으면 동일 인스턴스 재사용.
    judge_llm = gen_llm if adapter is None else MlxLLM(settings.mlx_model)
    judge_fn = lambda prompt: "".join(judge_llm.stream(
        [{"role": "user", "content": prompt}], max_tokens=16, temperature=0.0))
```
그리고 `run_item(... llm=llm ...)` 호출의 `llm=llm`을 `llm=gen_llm`으로 변경.

- [ ] **Step 2: 임포트 + 인자 파싱 확인 (모델 로딩 없이)**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package eval python -c "import eval.cli, sys; print('cli ok; mlx loaded:', 'mlx' in sys.modules)"`
Expected: `cli ok; mlx loaded: False`.

- [ ] **Step 3: eval 빠른 테스트 회귀**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/eval && uv run pytest -m "not slow" -q`
Expected: 통과(cli는 단위 테스트 없음, 순수 모듈 23개 영향 없음).

- [ ] **Step 4: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/eval/src/eval/cli.py
git commit -m "feat(eval): add --adapter to eval CLI (gen=adapter, judge=base)"
```

---

## Task 3: 학습 커맨드 빌더

**Files:**
- Create: `packages/finetune/src/finetune/train.py`
- Test: `packages/finetune/tests/test_train.py`

`mlx_lm.lora` 학습 명령을 순수 함수로 구성(라이브 실행은 Task 5에서 subprocess). 플래그는 mlx-lm 0.31.3 기준(`--num-layers`/`--learning-rate`/`--adapter-path`).

- [ ] **Step 1: 실패하는 테스트** — `packages/finetune/tests/test_train.py`:
```python
from finetune.train import build_lora_command


def test_command_has_required_flags():
    cmd = build_lora_command(model="m", data_dir="data/ft",
                             adapter_dir="data/adapters/qlora",
                             iters=200, batch_size=1, num_layers=8,
                             learning_rate=1e-5)
    assert cmd[:4] == ["python", "-m", "mlx_lm.lora", "--model"]
    assert "--train" in cmd
    assert cmd[cmd.index("--data") + 1] == "data/ft"
    assert cmd[cmd.index("--adapter-path") + 1] == "data/adapters/qlora"
    assert cmd[cmd.index("--iters") + 1] == "200"
    assert cmd[cmd.index("--num-layers") + 1] == "8"
    assert cmd[cmd.index("--batch-size") + 1] == "1"
    assert cmd[cmd.index("--learning-rate") + 1] == "1e-05"


def test_defaults():
    cmd = build_lora_command(model="m", data_dir="d", adapter_dir="a")
    assert "--iters" in cmd and "--adapter-path" in cmd
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/finetune && uv run pytest tests/test_train.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'finetune.train'`

- [ ] **Step 3: 구현** — `packages/finetune/src/finetune/train.py`:
```python
"""mlx_lm.lora QLoRA 학습 명령 빌더(라이브 실행은 호출 측에서 subprocess)."""


def build_lora_command(*, model: str, data_dir: str, adapter_dir: str,
                       iters: int = 300, batch_size: int = 1,
                       num_layers: int = 8, learning_rate: float = 1e-5) -> list[str]:
    """mlx-lm 0.31.3 기준 LoRA 학습 명령(list[str])."""
    return [
        "python", "-m", "mlx_lm.lora",
        "--model", model,
        "--train",
        "--data", str(data_dir),
        "--adapter-path", str(adapter_dir),
        "--iters", str(iters),
        "--batch-size", str(batch_size),
        "--num-layers", str(num_layers),
        "--learning-rate", str(learning_rate),
    ]
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/finetune && uv run pytest tests/test_train.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/finetune/src/finetune/train.py packages/finetune/tests/test_train.py
git commit -m "feat(finetune): add mlx_lm.lora command builder"
```

---

## Task 4: A/B 비교 모듈

**Files:**
- Create: `packages/finetune/src/finetune/compare.py`
- Test: `packages/finetune/tests/test_compare.py`

두 평가 리포트(baseline.json / qlora.json)의 요약 지표를 읽어 지표별 델타를 내고 마크다운 표로 만든다.

- [ ] **Step 1: 실패하는 테스트** — `packages/finetune/tests/test_compare.py`:
```python
import json

from finetune.compare import load_summary, compare_runs, to_markdown


def test_load_summary_reads_summary_block(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"label": "x", "summary": {"recall_at_k": 0.8},
                             "items": []}), encoding="utf-8")
    assert load_summary(p) == {"recall_at_k": 0.8}


def test_compare_runs_computes_deltas():
    base = {"recall_at_k": 0.81, "structure_rate": 0.75, "citation_rate": 1.0,
            "groundedness": 0.69}
    qlora = {"recall_at_k": 0.81, "structure_rate": 0.94, "citation_rate": 1.0,
             "groundedness": 0.78}
    cmp = compare_runs(base, qlora)
    assert cmp["structure_rate"] == {"baseline": 0.75, "qlora": 0.94, "delta": 0.19}
    assert cmp["recall_at_k"]["delta"] == 0.0       # 검색 동일 → 불변
    assert cmp["citation_rate"]["delta"] == 0.0


def test_compare_only_common_metrics():
    cmp = compare_runs({"a": 1.0}, {"b": 2.0})
    assert cmp == {}


def test_to_markdown_table():
    cmp = {"structure_rate": {"baseline": 0.75, "qlora": 0.94, "delta": 0.19}}
    md = to_markdown(cmp)
    assert "structure_rate" in md
    assert "+0.19" in md or "0.19" in md
    assert "|" in md      # 표 형식
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/finetune && uv run pytest tests/test_compare.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'finetune.compare'`

- [ ] **Step 3: 구현** — `packages/finetune/src/finetune/compare.py`:
```python
"""A/B 비교: baseline vs qlora 평가 요약 → 지표별 델타 + 마크다운."""
import json
from pathlib import Path

_METRICS = ["recall_at_k", "citation_rate", "structure_rate", "disclaimer_rate",
            "sources_rate", "mention_coverage", "groundedness"]


def load_summary(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["summary"]


def compare_runs(baseline: dict, qlora: dict) -> dict:
    out = {}
    for m in _METRICS:
        if m in baseline and m in qlora:
            out[m] = {"baseline": baseline[m], "qlora": qlora[m],
                      "delta": round(qlora[m] - baseline[m], 4)}
    return out


def to_markdown(comparison: dict) -> str:
    lines = ["| 지표 | baseline | qlora | Δ |", "|---|---|---|---|"]
    for m, v in comparison.items():
        lines.append(f"| {m} | {v['baseline']:.3f} | {v['qlora']:.3f} | {v['delta']:+.3f} |")
    return "\n".join(lines)
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/finetune && uv run pytest tests/test_compare.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: compare_cli (결론 문서 생성기)** — `packages/finetune/src/finetune/compare_cli.py`:
```python
"""baseline.json vs qlora.json → A/B 결론 문서 출력.

실행: uv run --package finetune python -m finetune.compare_cli
"""
from pathlib import Path

from .compare import compare_runs, load_summary, to_markdown

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RUNS = _REPO_ROOT / "data" / "eval_runs"


def main() -> None:
    base = load_summary(_RUNS / "baseline.json")
    qlora = load_summary(_RUNS / "qlora.json")
    cmp = compare_runs(base, qlora)
    print(to_markdown(cmp))


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 전체 finetune 빠른 테스트**
Run: `cd /Users/fujii0711/Claude/privateLLM/packages/finetune && uv run pytest -m "not slow" -q`
Expected: 통과(train 2 + compare 4).

- [ ] **Step 7: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/finetune/src/finetune/compare.py packages/finetune/src/finetune/compare_cli.py packages/finetune/tests/test_compare.py
git commit -m "feat(finetune): add A/B comparison module + CLI"
```

---

## Task 5: 라이브 — 학습 + A/B 측정 + 결론

**Files:** 없음(라이브 실행). 산출물 `data/adapters/`·`data/eval_runs/`(gitignore). 결론은 `docs/superpowers/notes/`에 커밋.

- [ ] **Step 1: 학습 데이터 존재 확인 (없으면 재빌드)**
```bash
cd /Users/fujii0711/Claude/privateLLM
ls -la data/ft/train.jsonl data/ft/valid.jsonl 2>/dev/null \
  || uv run --package ftdata python -m ftdata.cli --k 4 --per-q 2 --min-ground 0.5
wc -l data/ft/train.jsonl data/ft/valid.jsonl
```
Expected: train ~45줄, valid ~4줄.

- [ ] **Step 2: QLoRA 어댑터 학습 (MLX, 수 분)**
먼저 명령을 빌더로 확인 후 실행:
```bash
cd /Users/fujii0711/Claude/privateLLM
uv run --package finetune python -c "
from finetune.train import build_lora_command
print(' '.join(build_lora_command(model='mlx-community/Qwen2.5-7B-Instruct-4bit',
      data_dir='data/ft', adapter_dir='data/adapters/qlora',
      iters=300, batch_size=1, num_layers=8, learning_rate=1e-5)))
"
# 위 명령을 실제 실행 (uv 환경에서)
uv run --package finetune python -m mlx_lm.lora \
  --model mlx-community/Qwen2.5-7B-Instruct-4bit --train \
  --data data/ft --adapter-path data/adapters/qlora \
  --iters 300 --batch-size 1 --num-layers 8 --learning-rate 1e-5 2>&1 | tail -25
```
Expected: 학습 진행(train/val loss 로그) 후 `data/adapters/qlora/adapters.safetensors` + `adapter_config.json` 생성.
> **mlx-lm 데이터 형식:** `--data data/ft`는 `train.jsonl`·`valid.jsonl`을 읽는다. chat 형식(`{"messages":[...]}`)을 mlx-lm가 지원. 만약 `test.jsonl` 부재로 에러가 나면 `cp data/ft/valid.jsonl data/ft/test.jsonl` 후 재시도.
> **val loss가 train loss 대비 크게 발산하면(과적합)** `--iters`를 줄이거나(예 150) `--num-layers`를 줄여 재학습. 45 train·4 valid라 과적합 위험이 있으니 로그를 보고 판단.

- [ ] **Step 3: A/B 측정 — 같은 세션에서 baseline과 qlora 둘 다 (각 ~6분)**
```bash
cd /Users/fujii0711/Claude/privateLLM
# baseline (base 모델) — 동일 코드/조건으로 재측정
uv run --package eval python -m eval.cli --label baseline
# qlora (base+adapter; judge는 base)
uv run --package eval python -m eval.cli --label qlora --adapter data/adapters/qlora
```
Expected: 각각 `data/eval_runs/baseline.json`·`qlora.json` 저장 + 요약 출력.
검색은 양 arm 동일하므로 `recall_at_k`는 같아야 한다(다르면 버그 — 보고).

- [ ] **Step 4: A/B 비교**
```bash
cd /Users/fujii0711/Claude/privateLLM
uv run --package finetune python -m finetune.compare_cli
```
Expected: 지표별 baseline/qlora/Δ 마크다운 표 출력.

- [ ] **Step 5: 결론 해석 + 문서 커밋**
표를 해석한다(정직하게 — 개선이든 무변화든 하락이든 측정값 그대로):
- `recall_at_k` Δ≈0 (검색 동일 — 검증 포인트). 0이 아니면 측정 버그.
- `structure_rate`·`mention_coverage`·`groundedness`: QLoRA가 올릴 것으로 기대한 헤드룸. Δ가 핵심 결론.
- `citation_rate`·`disclaimer_rate`: 베이스라인이 이미 1.0(프롬프트/결정적 보장) → Δ≈0 예상.
- 소규모(45 train)·자기-distillation이라 개선 폭이 작거나 과적합으로 하락할 수도 있음 — **결과를 정직하게 보고**(파인튜닝이 항상 개선을 보장하지 않는다는 것도 유효한 연구 결과).

결론 문서 작성·커밋:
```bash
cd /Users/fujii0711/Claude/privateLLM
mkdir -p docs/superpowers/notes
uv run --package finetune python -c "
import pathlib
from finetune.compare import load_summary, compare_runs, to_markdown
runs = pathlib.Path('data/eval_runs')
base = load_summary(runs/'baseline.json'); ql = load_summary(runs/'qlora.json')
table = to_markdown(compare_runs(base, ql))
pathlib.Path('docs/superpowers/notes/ab-result.md').write_text(
    '# QLoRA A/B 결과 (RAG only vs RAG + QLoRA 어댑터)\n\n'
    '평가셋: packages/eval/eval_set.jsonl (16문항, 학습 질문과 disjoint)\n'
    '어댑터: data/ft(train 45/valid 4)로 mlx_lm.lora 학습. 양 arm temp 0.2, judge=base.\n\n'
    + table + '\n\n'
    '검색은 양 arm 동일하므로 recall_at_k는 불변이어야 한다. '
    'structure_rate·groundedness·mention_coverage가 QLoRA의 형식·충실도 기여를 나타낸다.\n', encoding='utf-8')
print('기록됨'); print(table)
"
git add docs/superpowers/notes/ab-result.md
git commit -m "docs(finetune): record QLoRA A/B result"
```

---

## 완료 기준 (Definition of Done)

- [ ] `cd packages/finetune && uv run pytest -m "not slow"` 통과(train 2 + compare 4). api·eval 회귀 통과.
- [ ] `data/adapters/qlora/`에 학습된 어댑터 존재.
- [ ] `eval.cli --adapter`로 qlora arm 측정 → `data/eval_runs/qlora.json` 생성.
- [ ] `finetune.compare_cli`가 baseline vs qlora 델타 표 출력.
- [ ] `docs/superpowers/notes/ab-result.md`에 A/B 결과 표 + 해석 커밋.
- [ ] `recall_at_k` Δ≈0 확인(검색 동일 — A/B 측정 정합성 검증).

이 시점에서 **파인튜닝의 정량적 기여도(A/B)가 산출**된다 → 전체 연구(Plan 1~3) 완료.

---

## 후속 / 한계

- **결과가 미미하거나 하락 시** (소규모 데이터·자기-distillation 한계): 정직하게 보고하는 것이 연구 결과. 개선 경로 — (a) Plan 3B 데이터 확장(`--k`·질문풀↑), (b) 더 강한 teacher(Qwen2.5-32B-4bit), (c) 실제 생활법령/상담사례(`해설`/`상담사례`) 보강, (d) 하이퍼파라미터 튜닝(iters/num-layers/lr).
- **재현:** 데이터·어댑터·평가결과 모두 `data/`(gitignore) — 재생성 가능 아티팩트. 코드(packages/*)와 결론 문서(docs/notes)만 버전관리. 전체 재현: ftdata.cli → mlx_lm.lora → eval.cli ×2 → compare_cli.
- **배포 시:** 어댑터를 `api/settings.py`에 `MLX_ADAPTER` env로 노출하면 운영에서 base/어댑터 전환 가능(현재는 eval A/B용 `--adapter`만).
