# 계획 2A — RAG 코어 + FastAPI `/chat` 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Plan 1이 구축한 Chroma 인덱스(`jeonse_deposit`) 위에, 질의를 검색해 근거를 주입하고 MLX Qwen2.5-7B로 상담형 답변(`[n]` 인용 포함)을 스트리밍 생성하는 FastAPI `/chat` 엔드포인트를 만든다. `curl`로 데모 가능한 RAG 베이스라인 챗 API가 완성 산출물.

**Architecture:** uv 워크스페이스 모노레포. `packages/rag`(검색·프롬프트 조립·인용 매핑 — Plan 3 평가와 공유)와 `apps/api`(FastAPI + MLX 서빙)로 분리. 데이터 흐름: `질의 → rag.retrieve(bge-m3+Chroma) → rag.build_prompt → api.llm.stream(MLX) → rag.map_citations → SSE(answer 토큰 + sources)`. LLM과 임베더는 주입 가능하게 설계해 네트워크/GPU 없이 단위 테스트한다.

**Tech Stack:** Python 3.11, uv (workspace), FastAPI, uvicorn, sse-starlette, pydantic, chromadb, sentence-transformers(bge-m3), mlx-lm(Qwen2.5-7B-Instruct-4bit), pytest, httpx(TestClient).

**Scope (YAGNI):** 이 계획은 **백엔드만**. Next.js UI는 Plan 2B. 파인튜닝/평가는 Plan 3. 멀티턴 대화 히스토리·인증·세션 저장은 범위 밖(단일 질의 → 단일 답변). 리랭커는 범위 밖(Plan 1에서 선택 사항으로 남김 — 필요 시 후속).

---

## 사전 준비 (수동, 1회)

MLX용 Qwen2.5-7B 4bit 모델(~4.3GB)이 필요하다. Hugging Face에서 자동 다운로드되며, 최초 1회만 받는다.
- 모델: `mlx-community/Qwen2.5-7B-Instruct-4bit`
- 코드 작성·단위 테스트는 모델 없이 진행 가능(가짜 LLM 주입). **실제 모델은 Task 8의 slow 테스트와 Task 12 라이브 스모크에서만 필요.**

전제: Plan 1 완료 상태(`data/chroma`에 `jeonse_deposit` 컬렉션 1264 청크, bge-m3 1024-dim cosine). `data/`는 gitignore됨.

---

## File Structure

```
privateLLM/
├── pyproject.toml                  # [신규] uv 워크스페이스 루트 (members: pipelines, packages/*, apps/*)
├── packages/
│   └── rag/
│       ├── pyproject.toml          # rag 패키지
│       ├── src/rag/
│       │   ├── __init__.py
│       │   ├── config.py           # RagConfig (chroma_dir/collection/model/k/threshold) — OC 불필요
│       │   ├── types.py            # Retrieved, Source 데이터클래스
│       │   ├── embedder.py         # bge-m3 질의 임베더 (encode_fn 주입)
│       │   ├── retriever.py        # Chroma top-k → list[Retrieved] + grounding 판정
│       │   ├── prompt.py           # 시스템 프롬프트 + 근거 번호 매김 + chat messages 조립
│       │   └── citations.py        # 답변의 [n] 파싱·검증 → Source 매핑(환각 인용 제거)
│       └── tests/
│           ├── conftest.py
│           ├── test_config.py
│           ├── test_retriever.py
│           ├── test_prompt.py
│           └── test_citations.py
└── apps/
    └── api/
        ├── pyproject.toml          # api 패키지 (rag 경로 의존)
        ├── src/api/
        │   ├── __init__.py
        │   ├── settings.py         # 환경 설정 (모델명, chroma 경로, 생성 파라미터)
        │   ├── schemas.py          # pydantic ChatRequest/Source/...
        │   ├── llm.py              # MLX Qwen 로더 + stream 생성 (LLM 프로토콜, 주입 가능)
        │   ├── pipeline.py         # RAG 오케스트레이션 (retrieve→prompt→generate→cite)
        │   └── main.py             # FastAPI app: POST /chat (SSE), GET /health
        └── tests/
            ├── conftest.py
            ├── test_pipeline.py
            └── test_chat_endpoint.py
```

루트 워크스페이스로 묶으면 `uv run --package rag pytest` / `uv run --package api ...` 형태로 실행. 기존 `pipelines`는 워크스페이스 멤버로 편입하되 코드 변경은 없다.

---

## Task 0: uv 워크스페이스 + rag 패키지 스캐폴딩

**Files:**
- Create: `pyproject.toml` (repo root)
- Create: `packages/rag/pyproject.toml`
- Create: `packages/rag/src/rag/__init__.py` (빈 파일)
- Create: `packages/rag/tests/conftest.py`

- [ ] **Step 1: 루트 워크스페이스 pyproject.toml**

`pyproject.toml` (repo root):
```toml
[tool.uv.workspace]
members = ["pipelines", "packages/*", "apps/*"]
```

- [ ] **Step 2: rag 패키지 pyproject.toml**

`packages/rag/pyproject.toml`:
```toml
[project]
name = "rag"
version = "0.1.0"
description = "주택임대차 보증금 반환 챗봇 — RAG 검색·프롬프트·인용 코어"
requires-python = ">=3.11"
dependencies = [
    "chromadb>=0.5",
    "sentence-transformers>=3.0",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["slow: 실제 모델/인덱스를 쓰는 느린 테스트"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/rag"]
```

- [ ] **Step 3: 패키지 init + conftest**

`packages/rag/src/rag/__init__.py`: (빈 파일)

`packages/rag/tests/conftest.py`:
```python
import chromadb
import pytest


@pytest.fixture
def fake_chroma(tmp_path):
    """결정적 2차원 가짜 임베딩으로 채운 임시 Chroma 컬렉션 경로를 돌려준다.

    임베딩 규칙: 텍스트에 '보증금'이 있으면 [1,0], 아니면 [0,1].
    질의도 같은 규칙으로 임베딩하면 '보증금' 청크가 가깝게 검색된다.
    """
    from rag.config import COLLECTION  # 지연 import: Task 1 전 수집 단계가 깨지지 않게

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    rows = [
        ("law-1", "임차인은 보증금을 우선변제 받을 수 있다", "법령",
         "주택임대차보호법 제3조의2(보증금의 회수)", "제3조의2", "https://law/1", "2023-07-19"),
        ("law-2", "임대차 기간은 2년으로 본다", "법령",
         "주택임대차보호법 제4조(임대차기간)", "제4조", "https://law/2", "2023-07-19"),
        ("prec-1", "보증금 반환과 주택 인도는 동시이행 관계이다", "판례",
         "대법원 2020다1 임차보증금반환", "판결요지", "https://law/p1", "2021-01-15"),
    ]
    def emb(t): return [1.0, 0.0] if "보증금" in t else [0.0, 1.0]
    col.add(
        ids=[r[0] for r in rows],
        documents=[r[1] for r in rows],
        embeddings=[emb(r[1]) for r in rows],
        metadatas=[{"source_type": r[2], "title": r[3], "ref": r[4],
                    "url": r[5], "date": r[6]} for r in rows],
    )
    return tmp_path / "chroma"


@pytest.fixture
def fake_encode():
    """conftest의 fake_chroma와 동일한 임베딩 규칙."""
    def _encode(texts):
        return [[1.0, 0.0] if "보증금" in t else [0.0, 1.0] for t in texts]
    return _encode
```

- [ ] **Step 4: 워크스페이스 동기화**

Run: `cd /Users/fujii0711/Claude/privateLLM && uv sync`
Expected: 워크스페이스가 `pipelines`, `rag`(및 아직 없는 apps는 무시)를 인식, 의존성 설치 성공. 루트 `uv.lock` 생성/갱신.

> **중요 — pipelines 락파일 통합:** Plan 1에서 `pipelines/`는 독립 uv 프로젝트라 자체 `pipelines/uv.lock`을 가진다. 워크스페이스 멤버가 되면 락은 루트 단일 `uv.lock`로 통합되므로 **`pipelines/uv.lock`을 삭제**한다(`git rm pipelines/uv.lock`). 통합 후 기존 파이프라인 테스트가 여전히 통과하는지 확인: `uv run --package pipelines pytest -m "not slow" -q` (37개 중 빠른 것 통과). pipelines의 소스/테스트 코드는 변경하지 않는다.
> 만약 `apps/*` glob이 비어 있어 경고가 나면 무시(Task 6에서 채움). 멤버가 0개여서 에러가 나면 일단 `members = ["pipelines", "packages/*"]`로 두고 Task 6에서 `apps/*` 추가.

- [ ] **Step 5: pytest 수집 확인**

Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest -q`
Expected: `no tests ran` (임포트 에러 없음). conftest가 `rag.config.COLLECTION`을 import하므로 Task 1 전에는 수집 단계에서 ModuleNotFound가 날 수 있음 — 그 경우 Step 5는 Task 1 완료 후 재실행(여기서는 워크스페이스 인식만 확인).

- [ ] **Step 6: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git checkout -b plan2a-rag-api
git add pyproject.toml packages/rag/ uv.lock
git commit -m "chore(rag): scaffold uv workspace + rag package"
```

---

## Task 1: RagConfig + 상수

**Files:**
- Create: `packages/rag/src/rag/config.py`
- Test: `packages/rag/tests/test_config.py`

Plan 1과 **반드시 동일한** 임베딩 모델·컬렉션·cosine 규약을 상수로 고정한다(불일치 시 검색이 깨짐).

- [ ] **Step 1: 실패하는 테스트** — `packages/rag/tests/test_config.py`:
```python
from pathlib import Path

from rag.config import RagConfig, COLLECTION, MODEL_NAME


def test_constants_match_pipeline_contract():
    # Plan 1이 색인할 때 쓴 값과 동일해야 한다
    assert COLLECTION == "jeonse_deposit"
    assert MODEL_NAME == "BAAI/bge-m3"


def test_defaults(tmp_path):
    cfg = RagConfig(chroma_dir=tmp_path)
    assert cfg.collection == "jeonse_deposit"
    assert cfg.model_name == "BAAI/bge-m3"
    assert cfg.top_k == 6
    assert 0.0 < cfg.min_similarity < 1.0


def test_from_env_reads_chroma_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "c"))
    cfg = RagConfig.from_env()
    assert cfg.chroma_dir == tmp_path / "c"
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag.config'`

- [ ] **Step 3: 구현** — `packages/rag/src/rag/config.py`:
```python
import os
from dataclasses import dataclass
from pathlib import Path

# Plan 1(pipelines)이 색인 시 사용한 값과 동일해야 한다.
COLLECTION = "jeonse_deposit"
MODEL_NAME = "BAAI/bge-m3"

# data/chroma 기본 위치(레포 루트 기준). config.py: packages/rag/src/rag/config.py
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CHROMA = _REPO_ROOT / "data" / "chroma"


@dataclass
class RagConfig:
    chroma_dir: Path = _DEFAULT_CHROMA
    collection: str = COLLECTION
    model_name: str = MODEL_NAME
    top_k: int = 6
    min_similarity: float = 0.35   # cosine 유사도 하한(이하면 grounding 약함으로 처리)

    @classmethod
    def from_env(cls) -> "RagConfig":
        chroma = os.environ.get("CHROMA_DIR")
        return cls(chroma_dir=Path(chroma) if chroma else _DEFAULT_CHROMA)
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_config.py -v`
Expected: PASS (3 passed)

> `min_similarity=0.35`는 Plan 1 라이브에서 적합 결과가 cosine distance ~0.28–0.42(유사도 ~0.58–0.72)였던 것에 근거한 보수적 기본값. retriever에서 유사도 = `1 - distance`로 환산해 사용.

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/rag/src/rag/config.py packages/rag/tests/test_config.py
git commit -m "feat(rag): add RagConfig + pipeline-matching constants"
```

---

## Task 2: 타입 + 질의 임베더

**Files:**
- Create: `packages/rag/src/rag/types.py`
- Create: `packages/rag/src/rag/embedder.py`
- Test: `packages/rag/tests/test_embedder.py`

- [ ] **Step 1: 실패하는 테스트** — `packages/rag/tests/test_embedder.py`:
```python
import pytest

from rag.embedder import QueryEmbedder


def test_embeds_with_injected_fn():
    emb = QueryEmbedder(encode_fn=lambda texts: [[0.5, 0.5] for _ in texts])
    assert emb.embed_query("보증금 반환") == [0.5, 0.5]


@pytest.mark.slow
def test_real_bge_m3_dim():
    emb = QueryEmbedder()
    v = emb.embed_query("전세 보증금을 못 받았어요")
    assert len(v) == 1024
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_embedder.py -v -m "not slow"`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag.embedder'`

- [ ] **Step 3: 구현**

`packages/rag/src/rag/types.py`:
```python
from dataclasses import dataclass


@dataclass
class Retrieved:
    id: str
    text: str
    similarity: float          # cosine 유사도 (1 - distance)
    source_type: str
    title: str
    ref: str
    url: str
    date: str


@dataclass
class Source:
    n: int                     # 인용 번호 [n]
    title: str
    ref: str
    url: str
    source_type: str
```

`packages/rag/src/rag/embedder.py`:
```python
"""질의 임베더 — Plan 1과 동일한 bge-m3(1024-dim). encode_fn 주입으로 테스트 가능."""
from typing import Callable, Optional

from .config import MODEL_NAME


class QueryEmbedder:
    def __init__(self, encode_fn: Optional[Callable[[list[str]], list]] = None,
                 model_name: str = MODEL_NAME):
        self._encode_fn = encode_fn
        self._model_name = model_name
        self._model = None

    def _lazy(self, texts: list[str]) -> list:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import torch

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self._model = SentenceTransformer(self._model_name, device=device)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed_query(self, query: str) -> list:
        fn = self._encode_fn or self._lazy
        return fn([query])[0]
```

- [ ] **Step 4: 통과 확인 (fast)**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_embedder.py -v -m "not slow"`
Expected: PASS (1 passed, 1 deselected)

- [ ] **Step 5: 실제 모델 스모크 (느림, bge-m3 캐시됨)**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_embedder.py -v -m slow`
Expected: PASS (1 passed) — 1024-dim 확인.

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/rag/src/rag/types.py packages/rag/src/rag/embedder.py packages/rag/tests/test_embedder.py
git commit -m "feat(rag): add types + bge-m3 query embedder"
```

---

## Task 3: Retriever (Chroma top-k + grounding 판정)

**Files:**
- Create: `packages/rag/src/rag/retriever.py`
- Test: `packages/rag/tests/test_retriever.py`

- [ ] **Step 1: 실패하는 테스트** — `packages/rag/tests/test_retriever.py`:
```python
from rag.config import RagConfig
from rag.retriever import Retriever


def test_retrieves_topk_ordered(fake_chroma, fake_encode):
    cfg = RagConfig(chroma_dir=fake_chroma, top_k=2, min_similarity=0.1)
    r = Retriever(cfg, encode_fn=fake_encode)
    hits = r.retrieve("보증금을 못 받았어요")
    assert len(hits) == 2
    assert hits[0].id == "law-1"             # '보증금' 청크가 1위
    assert hits[0].title.startswith("주택임대차보호법")
    assert 0.0 <= hits[0].similarity <= 1.0
    assert hits[0].similarity >= hits[1].similarity


def test_is_grounded_true_when_strong_hit(fake_chroma, fake_encode):
    cfg = RagConfig(chroma_dir=fake_chroma, top_k=3, min_similarity=0.5)
    r = Retriever(cfg, encode_fn=fake_encode)
    hits = r.retrieve("보증금 우선변제")
    assert r.is_grounded(hits) is True       # 완전 일치(유사도 1.0) 존재


def test_is_grounded_false_when_all_weak(fake_chroma, fake_encode):
    # 질의에 '보증금'이 없으면 fake_encode가 [0,1] → '보증금' 청크와 직교(유사도 0)
    cfg = RagConfig(chroma_dir=fake_chroma, top_k=3, min_similarity=0.5)
    r = Retriever(cfg, encode_fn=fake_encode)
    hits = r.retrieve("날씨가 좋네요")
    assert r.is_grounded(hits) is False
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_retriever.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag.retriever'`

- [ ] **Step 3: 구현** — `packages/rag/src/rag/retriever.py`:
```python
"""Chroma top-k 검색 → Retrieved 리스트 + grounding 판정."""
import chromadb

from .config import RagConfig
from .embedder import QueryEmbedder
from .types import Retrieved


class Retriever:
    def __init__(self, config: RagConfig, encode_fn=None):
        self._cfg = config
        self._embedder = QueryEmbedder(encode_fn=encode_fn,
                                       model_name=config.model_name)
        client = chromadb.PersistentClient(path=str(config.chroma_dir))
        self._col = client.get_collection(config.collection)

    def retrieve(self, query: str) -> list[Retrieved]:
        qvec = self._embedder.embed_query(query)
        res = self._col.query(
            query_embeddings=[qvec], n_results=self._cfg.top_k,
            include=["documents", "metadatas", "distances"],
        )
        out: list[Retrieved] = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0],
                                   res["distances"][0]):
            out.append(Retrieved(
                id="",  # id는 query include에 불필요 — 사용처 없음
                text=doc,
                similarity=1.0 - float(dist),
                source_type=meta.get("source_type", ""),
                title=meta.get("title", ""),
                ref=meta.get("ref", ""),
                url=meta.get("url", ""),
                date=meta.get("date", ""),
            ))
        # id가 필요하면 res["ids"]도 매핑
        for r_, id_ in zip(out, res["ids"][0]):
            r_.id = id_
        return out

    def is_grounded(self, hits: list[Retrieved]) -> bool:
        return bool(hits) and hits[0].similarity >= self._cfg.min_similarity
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_retriever.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/rag/src/rag/retriever.py packages/rag/tests/test_retriever.py
git commit -m "feat(rag): add Chroma retriever with grounding check"
```

---

## Task 4: 프롬프트 빌더 (상담형 + 번호 매긴 근거)

**Files:**
- Create: `packages/rag/src/rag/prompt.py`
- Test: `packages/rag/tests/test_prompt.py`

- [ ] **Step 1: 실패하는 테스트** — `packages/rag/tests/test_prompt.py`:
```python
from rag.prompt import build_messages, SYSTEM_PROMPT
from rag.types import Retrieved


def _hit(text, title, sim=0.7):
    return Retrieved(id="x", text=text, similarity=sim, source_type="법령",
                     title=title, ref="제3조의2", url="https://law/1", date="2023-07-19")


def test_messages_have_system_and_user():
    hits = [_hit("임차인은 보증금을 우선변제 받는다", "주택임대차보호법 제3조의2")]
    msgs = build_messages("보증금 못 받았어요", hits)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == SYSTEM_PROMPT
    assert msgs[-1]["role"] == "user"


def test_user_message_numbers_sources_and_includes_query():
    hits = [
        _hit("임차인은 보증금을 우선변제 받는다", "주택임대차보호법 제3조의2"),
        _hit("동시이행 관계이다", "대법원 2020다1"),
    ]
    user = build_messages("보증금 못 받았어요", hits)[-1]["content"]
    assert "[1]" in user and "[2]" in user
    assert "주택임대차보호법 제3조의2" in user
    assert "임차인은 보증금을 우선변제" in user
    assert "보증금 못 받았어요" in user          # 사용자 질문 포함


def test_system_prompt_requires_citation_and_disclaimer():
    # 시스템 프롬프트가 핵심 행동 규칙을 담아야 한다
    assert "[" in SYSTEM_PROMPT and "근거" in SYSTEM_PROMPT
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_prompt.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag.prompt'`

- [ ] **Step 3: 구현** — `packages/rag/src/rag/prompt.py`:
```python
"""상담형 RAG 프롬프트 조립. 시스템 프롬프트 + 번호 매긴 근거 + 사용자 질문."""
from .types import Retrieved

SYSTEM_PROMPT = (
    "당신은 대한민국 주택임대차(특히 보증금 반환) 문제를 돕는 상담 도우미입니다. "
    "아래 '근거' 자료만 사용해 답하세요. 답변은 ① 상황 요약 ② 적용 법리 ③ 다음 절차 "
    "순의 상담형으로 작성합니다. 사실을 진술할 때는 반드시 해당 근거 번호를 [1], [2]처럼 "
    "문장 끝에 답니다. 근거에 없는 내용은 추측하지 말고, 근거가 부족하면 그 사실을 밝히세요. "
    "이 답변은 일반적 정보 제공이며 법률 자문이 아님을 마지막 줄에 고지하세요."
)


def build_messages(query: str, hits: list[Retrieved]) -> list[dict]:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[{i}] ({h.title}) {h.text}")
    grounds = "\n\n".join(blocks) if blocks else "(관련 근거 없음)"
    user = f"근거:\n{grounds}\n\n질문: {query}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_prompt.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/rag/src/rag/prompt.py packages/rag/tests/test_prompt.py
git commit -m "feat(rag): add consultation-style RAG prompt builder"
```

---

## Task 5: 인용 매핑 (환각 인용 제거)

**Files:**
- Create: `packages/rag/src/rag/citations.py`
- Test: `packages/rag/tests/test_citations.py`

생성된 답변에서 `[n]`을 추출해 실제 검색 근거와 대조한다. 범위를 벗어난 인용(환각)은 제거하고, 실제 인용된 근거만 `Source` 리스트로 반환한다.

- [ ] **Step 1: 실패하는 테스트** — `packages/rag/tests/test_citations.py`:
```python
from rag.citations import extract_sources, strip_invalid_citations
from rag.types import Retrieved


def _hits(n):
    return [Retrieved(id=f"i{i}", text=f"t{i}", similarity=0.7, source_type="법령",
                      title=f"제{i}조", ref=f"제{i}조", url=f"https://law/{i}",
                      date="2023-07-19") for i in range(1, n + 1)]


def test_extract_only_cited_sources_in_order():
    hits = _hits(3)
    answer = "보증금은 우선변제됩니다[1]. 인도와 동시이행입니다[3]."
    srcs = extract_sources(answer, hits)
    assert [s.n for s in srcs] == [1, 3]        # [2]는 인용 안 됨 → 제외
    assert srcs[0].title == "제1조" and srcs[0].url == "https://law/1"


def test_extract_dedupes_repeated_citation():
    hits = _hits(2)
    answer = "A[1]. B[1]. C[2]."
    assert [s.n for s in extract_sources(answer, hits)] == [1, 2]


def test_strip_invalid_citations_removes_out_of_range():
    hits = _hits(2)
    # [5]는 근거 범위 밖(환각) → 제거
    answer = "사실이다[1]. 또한[5]."
    assert strip_invalid_citations(answer, hits) == "사실이다[1]. 또한."


def test_extract_ignores_out_of_range():
    hits = _hits(2)
    answer = "맞다[1][9]."
    assert [s.n for s in extract_sources(answer, hits)] == [1]
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_citations.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag.citations'`

- [ ] **Step 3: 구현** — `packages/rag/src/rag/citations.py`:
```python
"""답변의 [n] 인용을 검증해 실제 근거(Source)로 매핑하고, 환각 인용을 제거한다."""
import re

from .types import Retrieved, Source

_CITE = re.compile(r"\[(\d+)\]")


def extract_sources(answer: str, hits: list[Retrieved]) -> list[Source]:
    """답변에 등장한 유효 인용 번호를 등장 순서대로(중복 제거) Source 리스트로 반환."""
    seen: set[int] = set()
    sources: list[Source] = []
    for m in _CITE.finditer(answer):
        n = int(m.group(1))
        if 1 <= n <= len(hits) and n not in seen:
            seen.add(n)
            h = hits[n - 1]
            sources.append(Source(n=n, title=h.title, ref=h.ref, url=h.url,
                                   source_type=h.source_type))
    return sources


def strip_invalid_citations(answer: str, hits: list[Retrieved]) -> str:
    """근거 범위를 벗어난 [n] 인용(환각)을 답변 텍스트에서 제거."""
    def repl(m):
        n = int(m.group(1))
        return m.group(0) if 1 <= n <= len(hits) else ""
    return _CITE.sub(repl, answer)
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest packages/rag/tests/test_citations.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 전체 rag 패키지 테스트**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest -m "not slow" -q`
Expected: 모든 rag 테스트 통과.

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add packages/rag/src/rag/citations.py packages/rag/tests/test_citations.py
git commit -m "feat(rag): add citation extraction + hallucinated-citation stripping"
```

---

## Task 6: api 패키지 스캐폴딩 + 설정 + 스키마

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/src/api/__init__.py` (빈 파일)
- Create: `apps/api/src/api/settings.py`
- Create: `apps/api/src/api/schemas.py`
- Create: `apps/api/tests/conftest.py`
- Test: `apps/api/tests/test_schemas.py`

- [ ] **Step 1: api pyproject (rag 경로 의존 + fastapi)**

`apps/api/pyproject.toml`:
```toml
[project]
name = "api"
version = "0.1.0"
description = "주택임대차 보증금 반환 챗봇 — FastAPI RAG 백엔드"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sse-starlette>=2.1",
    "pydantic>=2.7",
    "rag",
    "mlx-lm>=0.18",
]

[dependency-groups]
dev = ["pytest>=8.0", "httpx>=0.27"]

[tool.uv.sources]
rag = { workspace = true }

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["slow: 실제 MLX 모델을 쓰는 느린 테스트"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/api"]
```

- [ ] **Step 2: 워크스페이스에 apps 편입 확인 + 동기화**
루트 `pyproject.toml`의 `members`에 `apps/*`가 포함돼 있는지 확인(Task 0 Step 1에서 포함). 없으면 추가.
Run: `cd /Users/fujii0711/Claude/privateLLM && uv sync`
Expected: `api` 패키지 인식, fastapi/mlx-lm/sse-starlette 설치 성공.

- [ ] **Step 3: settings + 빈 init**

`apps/api/src/api/__init__.py`: (빈 파일)

`apps/api/src/api/settings.py`:
```python
import os
from dataclasses import dataclass, field

from rag.config import RagConfig

MLX_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"


@dataclass
class Settings:
    rag: RagConfig = field(default_factory=RagConfig.from_env)
    mlx_model: str = MLX_MODEL
    max_tokens: int = 768
    temperature: float = 0.3

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            rag=RagConfig.from_env(),
            mlx_model=os.environ.get("MLX_MODEL", MLX_MODEL),
        )
```

- [ ] **Step 4: 실패하는 스키마 테스트** — `apps/api/tests/test_schemas.py`:
```python
from api.schemas import ChatRequest, SourceOut


def test_chat_request_requires_message():
    req = ChatRequest(message="보증금 못 받았어요")
    assert req.message == "보증금 못 받았어요"


def test_source_out_shape():
    s = SourceOut(n=1, title="주택임대차보호법 제3조의2", ref="제3조의2",
                  url="https://law/1", source_type="법령")
    assert s.n == 1 and s.source_type == "법령"
```

`apps/api/tests/conftest.py`: (빈 파일, 추후 픽스처용)

- [ ] **Step 5: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.schemas'`

- [ ] **Step 6: 구현** — `apps/api/src/api/schemas.py`:
```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class SourceOut(BaseModel):
    n: int
    title: str
    ref: str
    url: str
    source_type: str
```

- [ ] **Step 7: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_schemas.py -v`
Expected: PASS (2 passed)

- [ ] **Step 8: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/api/pyproject.toml apps/api/src/api/__init__.py apps/api/src/api/settings.py apps/api/src/api/schemas.py apps/api/tests/ uv.lock
git commit -m "chore(api): scaffold FastAPI package + settings + schemas"
```

---

## Task 7: LLM 서비스 (MLX Qwen, 주입 가능 스트리밍)

**Files:**
- Create: `apps/api/src/api/llm.py`
- Test: `apps/api/tests/test_llm.py`

`LLM` 프로토콜은 `stream(messages) -> Iterator[str]`. 실제 구현 `MlxLLM`은 mlx-lm으로 토큰을 스트리밍한다. 테스트는 가짜 LLM으로 한다(모델 불필요).

- [ ] **Step 1: 실패하는 테스트** — `apps/api/tests/test_llm.py`:
```python
import pytest

from api.llm import FakeLLM


def test_fake_llm_streams_scripted_tokens():
    llm = FakeLLM(["안녕", "하세", "요"])
    msgs = [{"role": "user", "content": "x"}]
    assert list(llm.stream(msgs)) == ["안녕", "하세", "요"]


def test_fake_llm_full_text_helper():
    llm = FakeLLM(["a", "b", "c"])
    assert "".join(llm.stream([{"role": "user", "content": "x"}])) == "abc"


@pytest.mark.slow
def test_mlx_llm_generates_korean():
    from api.llm import MlxLLM
    llm = MlxLLM()  # 실제 모델 로딩(~4.3GB, 최초 1회 다운로드)
    msgs = [{"role": "system", "content": "한국어로 한 문장 답하세요."},
            {"role": "user", "content": "보증금 반환이 뭔가요?"}]
    text = "".join(llm.stream(msgs, max_tokens=64))
    assert text.strip()
    assert any("가" <= ch <= "힣" for ch in text)   # 한글 포함
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_llm.py -v -m "not slow"`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.llm'`

- [ ] **Step 3: 구현** — `apps/api/src/api/llm.py`:
```python
"""LLM 추상화 + MLX Qwen 구현. FakeLLM으로 모델 없이 테스트 가능."""
from typing import Iterator, Protocol

from .settings import MLX_MODEL


class LLM(Protocol):
    def stream(self, messages: list[dict], *, max_tokens: int = 768,
               temperature: float = 0.3) -> Iterator[str]:
        ...


class FakeLLM:
    """미리 정해진 토큰을 차례로 내보내는 테스트용 LLM."""
    def __init__(self, tokens: list[str]):
        self._tokens = tokens

    def stream(self, messages: list[dict], *, max_tokens: int = 768,
               temperature: float = 0.3) -> Iterator[str]:
        for t in self._tokens:
            yield t


class MlxLLM:
    """mlx-lm 기반 Qwen2.5-7B-Instruct-4bit 스트리밍 추론."""
    def __init__(self, model_name: str = MLX_MODEL):
        from mlx_lm import load
        self._model, self._tokenizer = load(model_name)

    def stream(self, messages: list[dict], *, max_tokens: int = 768,
               temperature: float = 0.3) -> Iterator[str]:
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler

        prompt = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False)
        sampler = make_sampler(temp=temperature)
        for resp in stream_generate(self._model, self._tokenizer, prompt,
                                    max_tokens=max_tokens, sampler=sampler):
            yield resp.text
```

- [ ] **Step 4: 통과 확인 (fast)**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_llm.py -v -m "not slow"`
Expected: PASS (2 passed, 1 deselected)

- [ ] **Step 5: 실제 MLX 스모크 (느림 — 최초 ~4.3GB 다운로드).**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_llm.py -v -m slow`
Expected: PASS (1 passed) — 한국어 문장 생성 확인. 최초 실행은 다운로드로 수 분.
> mlx-lm 버전에 따라 `stream_generate`/`make_sampler` 시그니처가 다를 수 있다. 실패 시 설치된 버전의 API에 맞춰 `MlxLLM.stream`만 조정(예: 구버전은 `stream_generate(model, tokenizer, prompt, max_tokens=...)`에 temp 인자 직접 전달). 테스트(FakeLLM 기반)는 건드리지 말 것. 조정 내용을 보고할 것.

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/api/src/api/llm.py apps/api/tests/test_llm.py
git commit -m "feat(api): add LLM abstraction + MLX Qwen streaming"
```

---

## Task 8: RAG 파이프라인 오케스트레이션

**Files:**
- Create: `apps/api/src/api/pipeline.py`
- Test: `apps/api/tests/test_pipeline.py`

`run_chat`은 retrieve → (grounding 판정) → prompt → LLM stream → 누적된 답변에서 인용 정리. 답변 토큰을 스트리밍하고, 마지막에 정리된 `sources`를 만든다. retriever와 llm을 주입받아 테스트한다.

- [ ] **Step 1: 실패하는 테스트** — `apps/api/tests/test_pipeline.py`:
```python
from api.llm import FakeLLM
from api.pipeline import run_chat
from rag.types import Retrieved


class StubRetriever:
    def __init__(self, hits, grounded=True):
        self._hits = hits
        self._grounded = grounded
    def retrieve(self, query):
        return self._hits
    def is_grounded(self, hits):
        return self._grounded


def _hit(n):
    return Retrieved(id=f"i{n}", text=f"근거{n}", similarity=0.7, source_type="법령",
                     title=f"주택임대차보호법 제{n}조", ref=f"제{n}조",
                     url=f"https://law/{n}", date="2023-07-19")


def test_run_chat_streams_answer_then_sources():
    retr = StubRetriever([_hit(1), _hit(2)])
    llm = FakeLLM(["보증금은 ", "우선변제[1] ", "됩니다."])
    events = list(run_chat("보증금?", retriever=retr, llm=llm))

    tokens = [e for e in events if e["type"] == "token"]
    final = [e for e in events if e["type"] == "done"][0]
    assert "".join(t["text"] for t in tokens) == "보증금은 우선변제[1] 됩니다."
    # 실제 인용된 [1]만 sources에 (그리고 [2]는 인용 안 됨)
    assert [s["n"] for s in final["sources"]] == [1]
    assert final["sources"][0]["url"] == "https://law/1"


def test_run_chat_strips_hallucinated_citation_from_final():
    retr = StubRetriever([_hit(1)])
    llm = FakeLLM(["사실[1] ", "환각[7]"])   # [7]은 근거 범위 밖
    events = list(run_chat("q", retriever=retr, llm=llm))
    final = [e for e in events if e["type"] == "done"][0]
    assert "[7]" not in final["answer"]
    assert [s["n"] for s in final["sources"]] == [1]


def test_run_chat_no_grounding_returns_fallback_without_calling_llm():
    called = {"n": 0}
    class LoudLLM:
        def stream(self, *a, **k):
            called["n"] += 1
            yield "should not happen"
    retr = StubRetriever([], grounded=False)
    events = list(run_chat("관련 없는 질문", retriever=retr, llm=LoudLLM()))
    final = [e for e in events if e["type"] == "done"][0]
    assert called["n"] == 0                       # 근거 없으면 LLM 호출 안 함
    assert "근거" in final["answer"]               # 안내 메시지
    assert final["sources"] == []
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.pipeline'`

- [ ] **Step 3: 구현** — `apps/api/src/api/pipeline.py`:
```python
"""RAG 오케스트레이션: 검색 → 근거 판정 → 프롬프트 → 스트리밍 생성 → 인용 정리."""
from typing import Iterator

from rag.citations import extract_sources, strip_invalid_citations
from rag.prompt import build_messages

NO_GROUNDING_MSG = (
    "죄송합니다. 질문과 충분히 관련된 근거(법령·판례)를 찾지 못했습니다. "
    "주택임대차 보증금 반환과 관련된 구체적 상황(예: 계약 종료 여부, 보증금 액수, "
    "임차권등기 여부 등)으로 다시 질문해 주세요.\n\n"
    "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다."
)


def run_chat(query: str, *, retriever, llm, max_tokens: int = 768,
            temperature: float = 0.3) -> Iterator[dict]:
    """이벤트 스트림을 yield한다.
    {"type":"token","text":...} (0개 이상) → {"type":"done","answer":str,"sources":[...]}
    """
    hits = retriever.retrieve(query)
    if not retriever.is_grounded(hits):
        yield {"type": "token", "text": NO_GROUNDING_MSG}
        yield {"type": "done", "answer": NO_GROUNDING_MSG, "sources": []}
        return

    messages = build_messages(query, hits)
    parts: list[str] = []
    for tok in llm.stream(messages, max_tokens=max_tokens, temperature=temperature):
        parts.append(tok)
        yield {"type": "token", "text": tok}

    raw = "".join(parts)
    answer = strip_invalid_citations(raw, hits)
    sources = [
        {"n": s.n, "title": s.title, "ref": s.ref, "url": s.url,
         "source_type": s.source_type}
        for s in extract_sources(answer, hits)
    ]
    yield {"type": "done", "answer": answer, "sources": sources}
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_pipeline.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/api/src/api/pipeline.py apps/api/tests/test_pipeline.py
git commit -m "feat(api): add RAG chat pipeline with grounding fallback + citation cleanup"
```

---

## Task 9: FastAPI `/chat` (SSE) + `/health`

**Files:**
- Create: `apps/api/src/api/main.py`
- Test: `apps/api/tests/test_chat_endpoint.py`

`/chat`은 SSE로 토큰을 흘리고 마지막에 `done`(answer+sources) 이벤트를 보낸다. 테스트는 의존성 주입(앱 state의 retriever/llm을 가짜로 교체)으로 모델 없이 한다.

- [ ] **Step 1: 실패하는 테스트** — `apps/api/tests/test_chat_endpoint.py`:
```python
import json

from fastapi.testclient import TestClient

from api.main import create_app
from api.llm import FakeLLM
from rag.types import Retrieved


class StubRetriever:
    def retrieve(self, query):
        return [Retrieved(id="i1", text="임차인은 보증금을 우선변제 받는다",
                          similarity=0.7, source_type="법령",
                          title="주택임대차보호법 제3조의2", ref="제3조의2",
                          url="https://law/1", date="2023-07-19")]
    def is_grounded(self, hits):
        return True


def _client():
    app = create_app(retriever=StubRetriever(),
                     llm=FakeLLM(["보증금은 ", "우선변제[1] 됩니다."]))
    return TestClient(app)


def test_health():
    assert _client().get("/health").json() == {"status": "ok"}


def test_chat_streams_sse_tokens_and_done():
    with _client() as client:
        with client.stream("POST", "/chat", json={"message": "보증금?"}) as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())
    # SSE 프레임 파싱: 'data: {...}\n\n'
    payloads = [json.loads(line[len("data: "):])
                for line in body.splitlines() if line.startswith("data: ")]
    types = [p["type"] for p in payloads]
    assert types[-1] == "done"
    done = payloads[-1]
    assert "우선변제" in done["answer"]
    assert done["sources"][0]["url"] == "https://law/1"


def test_chat_rejects_empty_message():
    assert _client().post("/chat", json={"message": ""}).status_code == 422
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_chat_endpoint.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'api.main'`

- [ ] **Step 3: 구현** — `apps/api/src/api/main.py`:
```python
"""FastAPI 앱: POST /chat (SSE 스트리밍), GET /health.

create_app(retriever=, llm=)로 의존성을 주입(테스트). 미주입 시 실제 구성."""
import json

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

from .pipeline import run_chat
from .schemas import ChatRequest
from .settings import Settings


def create_app(retriever=None, llm=None, settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="보증금 반환 RAG 챗봇")
    app.state.settings = settings or Settings.from_env()
    app.state.retriever = retriever
    app.state.llm = llm

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/chat")
    def chat(req: ChatRequest):
        retr = app.state.retriever or _build_retriever(app.state.settings)
        model = app.state.llm or _build_llm(app.state.settings)
        cfg = app.state.settings

        def event_gen():
            for ev in run_chat(req.message, retriever=retr, llm=model,
                               max_tokens=cfg.max_tokens, temperature=cfg.temperature):
                yield {"data": json.dumps(ev, ensure_ascii=False)}

        return EventSourceResponse(event_gen())

    return app


def _build_retriever(settings: Settings):
    from rag.retriever import Retriever
    if not hasattr(_build_retriever, "_cached"):
        _build_retriever._cached = Retriever(settings.rag)
    return _build_retriever._cached


def _build_llm(settings: Settings):
    from .llm import MlxLLM
    if not hasattr(_build_llm, "_cached"):
        _build_llm._cached = MlxLLM(settings.mlx_model)
    return _build_llm._cached


app = create_app()  # uvicorn api.main:app 용 (실제 구성, 지연 로딩)
```

> `app = create_app()`은 retriever/llm 미주입 → 첫 `/chat` 요청 때 `_build_*`가 실제 Retriever/MlxLLM을 지연 생성(모듈 import 시 모델 로딩하지 않도록). 이로써 `import api.main`이 가벼움(테스트가 모델을 안 건드림).

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_chat_endpoint.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 전체 api 테스트 (fast)**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest -m "not slow" -q`
Expected: 모든 api 테스트 통과.

- [ ] **Step 6: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/api/src/api/main.py apps/api/tests/test_chat_endpoint.py
git commit -m "feat(api): add /chat SSE endpoint + /health"
```

---

## Task 10: CORS + 도메인 가드 마무리 + 라이브 스모크

**Files:**
- Modify: `apps/api/src/api/main.py` (CORS 미들웨어 추가)
- Test: `apps/api/tests/test_cors.py`

Next.js(Plan 2B)가 브라우저에서 호출하므로 CORS가 필요하다. 도메인 밖 질문은 이미 grounding 판정(Task 8)으로 자연 차단되므로 별도 분류기는 YAGNI.

- [ ] **Step 1: 실패하는 CORS 테스트** — `apps/api/tests/test_cors.py`:
```python
from fastapi.testclient import TestClient

from api.main import create_app
from api.llm import FakeLLM


class StubRetriever:
    def retrieve(self, q): return []
    def is_grounded(self, h): return False


def test_cors_allows_localhost_3000():
    app = create_app(retriever=StubRetriever(), llm=FakeLLM([]))
    client = TestClient(app)
    resp = client.options(
        "/chat",
        headers={"Origin": "http://localhost:3000",
                 "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
```

- [ ] **Step 2: 실패 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_cors.py -v`
Expected: FAIL (CORS 헤더 없음)

- [ ] **Step 3: 구현** — `apps/api/src/api/main.py`의 `create_app`에 CORS 추가. `from fastapi.middleware.cors import CORSMiddleware` import 후, `app = FastAPI(...)` 직후:
```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

- [ ] **Step 4: 통과 확인**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package api pytest apps/api/tests/test_cors.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 전체 테스트 (rag + api, fast)**
Run: `cd /Users/fujii0711/Claude/privateLLM && uv run --package rag pytest -m "not slow" -q && uv run --package api pytest -m "not slow" -q`
Expected: 전부 통과.

- [ ] **Step 6: 라이브 엔드투엔드 스모크 (실제 MLX + 실제 Chroma).**
서버를 띄우고 실제 질의로 검증한다. 별도 터미널이 필요하면 사용자에게 요청하거나 백그라운드 실행:
```bash
cd /Users/fujii0711/Claude/privateLLM
# 서버 기동(백그라운드)
uv run --package api uvicorn api.main:app --port 8000 &
sleep 5   # 최초 요청에서 모델 로딩되므로 첫 호출이 느림
curl -N -s -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"전세 보증금을 집주인이 안 돌려줘요. 어떻게 해야 하나요?"}'
```
Expected: SSE로 상담형 답변 토큰이 흐르고, 마지막 `done` 이벤트에 `[1]` 등 인용과 함께 주택임대차보호법 제3조의2 등의 `sources`(title/url)가 포함됨. 답변이 ①상황요약 ②적용법리 ③다음절차 구조이고 마지막에 면책 고지가 있어야 함.
검증 후 서버 종료: `kill %1` (또는 해당 PID).
> 첫 호출은 Qwen2.5-7B 로딩으로 십수 초~수십 초 소요. 이후 호출은 빠름.

- [ ] **Step 7: Commit**
```bash
cd /Users/fujii0711/Claude/privateLLM
git add apps/api/src/api/main.py apps/api/tests/test_cors.py
git commit -m "feat(api): add CORS for Next.js dev origin"
```

---

## 완료 기준 (Definition of Done)

- [ ] `uv run --package rag pytest -m "not slow"` 및 `uv run --package api pytest -m "not slow"` 전부 통과.
- [ ] `rag` slow 테스트(bge-m3 1024-dim)와 `api` slow 테스트(MLX 한국어 생성) 통과.
- [ ] `uvicorn api.main:app` 기동 후 `curl /chat`이 SSE로 상담형 답변을 스트리밍하고, `done` 이벤트에 검증된 `[n]` 인용 + 출처(title/url) 포함.
- [ ] 보증금 반환 질의에 주택임대차보호법 제3조의2 등 올바른 근거가 인용됨.
- [ ] 도메인 밖/근거 없는 질의는 LLM 호출 없이 안내 메시지로 응답.

이 시점에서 **HTTP로 데모 가능한 RAG 베이스라인 챗 API**가 완성된다 → Plan 2B(Next.js UI)의 백엔드.

---

## 후속 계획으로의 인계

- **Plan 2B (Next.js UI):** `POST /chat` SSE(`data: {type:token|done}` 프레임)를 소비. `done.sources`로 출처 카드 렌더. CORS는 `http://localhost:3000` 허용됨. 응답 스키마: 토큰 이벤트 `{type:"token",text}`, 종료 `{type:"done",answer,sources:[{n,title,ref,url,source_type}]}`.
- **Plan 3 (평가 + QLoRA):** `packages/rag`(retriever/prompt/citations)를 평가 스크립트가 그대로 재사용(서빙과 동일 코드 → 평가 일관성). QLoRA 어댑터는 `MlxLLM(model_name=...)`에 어댑터 적용 버전을 추가해 A/B(베이스라인 vs 어댑터)로 교체. 베이스라인 점수는 이 API 기준으로 측정.
- **알려진 보완(Plan 1 리뷰 인계):** 청크 토큰 길이 가드, fetch_corpus 재시도/백오프, 질의 시 source_type 메타데이터 필터(현재 retriever는 전체 검색).
