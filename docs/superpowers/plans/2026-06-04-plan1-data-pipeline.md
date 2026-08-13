# 계획 1 — 데이터 파이프라인 (수집 → 정제 → 청킹 → 색인) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 주택임대차 보증금 반환 도메인의 법령·판례를 국가법령정보센터 OPEN API로 수집·정제·청킹하고 bge-m3로 임베딩해 Chroma 벡터 인덱스를 구축한다. CLI 질의로 검색이 동작함을 검증한다.

**Architecture:** Python(`uv`) 단일 패키지 `pipelines`. HTTP 클라이언트 → XML 파서 → 정규화 → 구조 인지 청킹 → bge-m3 임베딩 → Chroma 색인의 단방향 파이프라인. 외부 API 응답 형식의 불확실성은 "실제 호출로 fixture를 캡처한 뒤 그 fixture에 대해 TDD로 파서를 작성"하는 방식으로 제거한다.

**Tech Stack:** Python 3.11+, `uv`, `requests`, `lxml`, `sentence-transformers`(BAAI/bge-m3, MPS), `chromadb`, `pytest`.

**Scope note (YAGNI):** 이 계획의 RAG 코퍼스는 **API 기반·권위 있는 두 소스(법령 + 판례)** 로 한정한다. 스펙 5.1의 생활법령 해설·대한법률구조공단 상담사례(크롤링 기반, 깨지기 쉬움)는 파인튜닝 데이터로서 더 가치가 크므로 **계획 3(QLoRA 데이터셋)** 에서 수집한다. 청크 스키마의 `source_type`은 `해설`/`상담사례`까지 미리 허용해 두어 후속 계획이 같은 인덱스에 추가할 수 있게 한다.

---

## 사전 준비 (수동, 1회)

국가법령정보센터 OPEN API는 인증키로 **OC**(등록 이메일의 `@` 앞부분)를 사용한다.

1. https://open.law.go.kr 접속 → 회원가입/로그인.
2. "OPEN API" → "신청" 메뉴에서 `법령`, `판례` 활용 신청.
3. 승인되면 사용할 **OC 값**은 가입 이메일 아이디(예: `claude_devp_02@inswave.com` → OC=`claude_devp_02`)다.
4. 이 값을 Task 0에서 `pipelines/.env` 의 `LAW_API_OC` 에 넣는다.

> 승인 전이라도 코드 작성은 진행 가능하다. 실제 fixture 캡처(Task 3)와 통합 실행(Task 6, 11)에서만 OC가 필요하다.

---

## File Structure

```
pipelines/
├── pyproject.toml                 # uv 프로젝트 정의 + 의존성
├── .python-version                # 3.11
├── .env.example                   # LAW_API_OC 등 템플릿
├── README.md                      # 실행법
├── src/pipelines/
│   ├── __init__.py
│   ├── schema.py                  # Chunk TypedDict (스펙 5.3)
│   ├── config.py                  # 환경변수·경로 로딩
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── law_client.py          # law.go.kr HTTP 클라이언트(검색+본문 URL 빌드/호출)
│   │   ├── law_parser.py          # 법령 XML → 구조화 dict
│   │   ├── prec_parser.py         # 판례 XML → 구조화 dict
│   │   └── fetch_corpus.py        # 대상 법령·판례 수집 → data/raw/*.json
│   ├── clean/
│   │   ├── __init__.py
│   │   └── normalize.py           # 텍스트 정규화(공백·특수문자)
│   ├── chunk/
│   │   ├── __init__.py
│   │   └── chunker.py             # 구조 인지 청킹 → data/chunks/chunks.jsonl
│   ├── index/
│   │   ├── __init__.py
│   │   ├── embedder.py            # bge-m3 래퍼(주입 가능)
│   │   └── build_index.py         # 청크 임베딩 → Chroma
│   └── cli/
│       ├── __init__.py
│       └── query.py               # 검색 스모크 테스트 CLI
├── scripts/
│   └── capture_fixtures.py        # 실제 API 호출 → tests/fixtures 저장
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/                  # 캡처된 실제 XML + 샘플 청크
    ├── test_config.py
    ├── test_law_client.py
    ├── test_law_parser.py
    ├── test_prec_parser.py
    ├── test_normalize.py
    ├── test_chunker.py
    ├── test_embedder.py
    └── test_build_index.py
```

데이터 산출물(`data/`)과 모델 캐시(`models/`)는 `.gitignore` 처리됨(계획 0의 기존 커밋에서 설정 완료).

---

## Task 0: 프로젝트 스캐폴딩

**Files:**
- Create: `pipelines/pyproject.toml`
- Create: `pipelines/.python-version`
- Create: `pipelines/.env.example`
- Create: `pipelines/README.md`
- Create: `pipelines/src/pipelines/__init__.py`
- Create: `pipelines/tests/__init__.py`
- Create: `pipelines/tests/conftest.py`

- [ ] **Step 1: pyproject.toml 작성**

```toml
[project]
name = "pipelines"
version = "0.1.0"
description = "주택임대차 보증금 반환 챗봇 — 데이터 수집/색인 파이프라인"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
    "lxml>=5.0",
    "chromadb>=0.5",
    "sentence-transformers>=3.0",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
markers = ["slow: 실제 모델/네트워크를 쓰는 느린 테스트"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pipelines"]
```

- [ ] **Step 2: 보조 파일 작성**

`pipelines/.python-version`:
```
3.11
```

`pipelines/.env.example`:
```
# 국가법령정보센터 OPEN API 인증키(가입 이메일의 @ 앞부분)
LAW_API_OC=your_id_here
```

`pipelines/src/pipelines/__init__.py`: (빈 파일)

`pipelines/tests/__init__.py`: (빈 파일)

`pipelines/tests/conftest.py`:
```python
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
```

`pipelines/README.md`:
```markdown
# pipelines

주택임대차 보증금 반환 챗봇의 데이터 파이프라인.

## 설치
    cd pipelines
    uv sync

## 환경
    cp .env.example .env   # LAW_API_OC 채우기

## 실행
    uv run python -m pipelines.ingest.fetch_corpus   # 수집 → data/raw
    uv run python -m pipelines.chunk.chunker         # 청킹 → data/chunks
    uv run python -m pipelines.index.build_index     # 색인 → data/chroma
    uv run python -m pipelines.cli.query "보증금을 못 받았어요"

## 테스트
    uv run pytest            # 빠른 테스트
    uv run pytest -m slow    # 모델/네트워크 포함
```

- [ ] **Step 3: 의존성 설치 및 검증**

Run:
```bash
cd pipelines && uv sync
```
Expected: `.venv` 생성, 의존성 설치 성공. 마지막 줄에 설치된 패키지 수 표시.

- [ ] **Step 4: pytest 동작 확인 (테스트 0개)**

Run:
```bash
cd pipelines && uv run pytest -q
```
Expected: `no tests ran` (에러 없이 종료, exit code 5 또는 "collected 0 items"). 임포트 에러가 없어야 함.

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/
git commit -m "chore(pipelines): scaffold uv project for data pipeline"
```

---

## Task 1: 청크 스키마 정의

**Files:**
- Create: `pipelines/src/pipelines/schema.py`
- Test: `pipelines/tests/test_schema.py`

스펙 5.3의 청크 스키마를 코드로 고정한다. 이후 모든 task가 이 타입을 참조한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_schema.py`:
```python
from pipelines.schema import Chunk, SOURCE_TYPES, make_chunk


def test_make_chunk_fills_all_fields():
    c: Chunk = make_chunk(
        id="law-주택임대차보호법-3조의2",
        text="임차인은 ...",
        source_type="법령",
        title="주택임대차보호법 제3조의2",
        ref="제3조의2",
        url="https://www.law.go.kr/...",
        date="2023-07-19",
    )
    assert c["id"] == "law-주택임대차보호법-3조의2"
    assert c["source_type"] == "법령"
    assert set(c.keys()) == {"id", "text", "source_type", "title", "ref", "url", "date"}


def test_make_chunk_rejects_unknown_source_type():
    import pytest

    with pytest.raises(ValueError):
        make_chunk(id="x", text="t", source_type="기타",
                   title="t", ref="r", url="u", date="2023-01-01")


def test_source_types_constant():
    assert SOURCE_TYPES == ("법령", "판례", "해설", "상담사례")
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.schema'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/schema.py`:
```python
from typing import Literal, TypedDict

SOURCE_TYPES = ("법령", "판례", "해설", "상담사례")
SourceType = Literal["법령", "판례", "해설", "상담사례"]


class Chunk(TypedDict):
    id: str
    text: str
    source_type: SourceType
    title: str
    ref: str
    url: str
    date: str


def make_chunk(*, id: str, text: str, source_type: str, title: str,
               ref: str, url: str, date: str) -> Chunk:
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown source_type: {source_type!r}")
    return Chunk(id=id, text=text, source_type=source_type, title=title,
                 ref=ref, url=url, date=date)
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_schema.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/schema.py pipelines/tests/test_schema.py
git commit -m "feat(pipelines): add Chunk schema"
```

---

## Task 2: 설정 모듈 (경로 + OC 키)

**Files:**
- Create: `pipelines/src/pipelines/config.py`
- Test: `pipelines/tests/test_config.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_config.py`:
```python
from pathlib import Path

from pipelines.config import Config


def test_paths_are_under_data_root(tmp_path):
    cfg = Config(data_root=tmp_path, oc="testoc")
    assert cfg.raw_dir == tmp_path / "raw"
    assert cfg.chunks_dir == tmp_path / "chunks"
    assert cfg.chroma_dir == tmp_path / "chroma"


def test_ensure_dirs_creates_directories(tmp_path):
    cfg = Config(data_root=tmp_path, oc="testoc")
    cfg.ensure_dirs()
    assert cfg.raw_dir.is_dir()
    assert cfg.chunks_dir.is_dir()


def test_from_env_reads_oc(monkeypatch, tmp_path):
    monkeypatch.setenv("LAW_API_OC", "envoc")
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.oc == "envoc"
    assert cfg.data_root == tmp_path


def test_from_env_missing_oc_raises(monkeypatch):
    monkeypatch.delenv("LAW_API_OC", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="LAW_API_OC"):
        Config.from_env()
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.config'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/config.py`:
```python
import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


@dataclass
class Config:
    data_root: Path
    oc: str

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw"

    @property
    def chunks_dir(self) -> Path:
        return self.data_root / "chunks"

    @property
    def chroma_dir(self) -> Path:
        return self.data_root / "chroma"

    def ensure_dirs(self) -> None:
        for d in (self.raw_dir, self.chunks_dir, self.chroma_dir):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        oc = os.environ.get("LAW_API_OC")
        if not oc:
            raise RuntimeError(
                "LAW_API_OC 환경변수가 없습니다. pipelines/.env 를 설정하세요."
            )
        data_root = Path(os.environ.get("DATA_ROOT", str(DEFAULT_DATA_ROOT)))
        return cls(data_root=data_root, oc=oc)
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/config.py pipelines/tests/test_config.py
git commit -m "feat(pipelines): add Config (paths + OC key)"
```

---

## Task 3: law.go.kr HTTP 클라이언트 (URL 빌드 + 호출)

**Files:**
- Create: `pipelines/src/pipelines/ingest/__init__.py` (빈 파일)
- Create: `pipelines/src/pipelines/ingest/law_client.py`
- Test: `pipelines/tests/test_law_client.py`

URL 구성 규칙은 OPEN API 문서로 확정돼 있어 단위 테스트로 검증한다(네트워크 없이). 실제 HTTP 호출은 주입된 세션을 가짜로 대체해 테스트한다.

API 엔드포인트:
- 검색: `https://www.law.go.kr/DRF/lawSearch.do?OC={oc}&target={law|prec}&type=XML&query={q}&display={n}`
- 본문: `https://www.law.go.kr/DRF/lawService.do?OC={oc}&target={law|prec}&type=XML&{ID|MST}={id}`

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_law_client.py`:
```python
from urllib.parse import parse_qs, urlsplit

from pipelines.ingest.law_client import LawClient


class FakeResponse:
    def __init__(self, text): self.text = text; self.status_code = 200
    def raise_for_status(self): pass


class FakeSession:
    def __init__(self): self.calls = []
    def get(self, url, timeout=None):
        self.calls.append(url)
        return FakeResponse("<xml/>")


def _q(url):
    return {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}


def test_search_url_has_expected_params():
    sess = FakeSession()
    client = LawClient(oc="myoc", session=sess)
    client.search(target="law", query="주택임대차보호법", display=5)
    url = sess.calls[0]
    assert urlsplit(url).path == "/DRF/lawSearch.do"
    q = _q(url)
    assert q["OC"] == "myoc"
    assert q["target"] == "law"
    assert q["type"] == "XML"
    assert q["query"] == "주택임대차보호법"
    assert q["display"] == "5"


def test_fetch_law_uses_MST_param():
    sess = FakeSession()
    client = LawClient(oc="myoc", session=sess)
    client.fetch(target="law", id="123456")
    q = _q(sess.calls[0])
    assert urlsplit(sess.calls[0]).path == "/DRF/lawService.do"
    assert q["MST"] == "123456"
    assert q["target"] == "law"


def test_fetch_prec_uses_ID_param():
    sess = FakeSession()
    client = LawClient(oc="myoc", session=sess)
    client.fetch(target="prec", id="98765")
    q = _q(sess.calls[0])
    assert q["ID"] == "98765"
    assert q["target"] == "prec"


def test_returns_response_text():
    client = LawClient(oc="myoc", session=FakeSession())
    assert client.search(target="prec", query="보증금") == "<xml/>"
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_law_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.ingest.law_client'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/ingest/__init__.py`: (빈 파일)

`pipelines/src/pipelines/ingest/law_client.py`:
```python
from urllib.parse import urlencode

import requests

BASE = "https://www.law.go.kr/DRF"
# target별 본문 식별자 파라미터: 법령은 MST(법령일련번호), 판례는 ID(판례일련번호)
_ID_PARAM = {"law": "MST", "prec": "ID"}


class LawClient:
    def __init__(self, oc: str, session=None, timeout: int = 20):
        self.oc = oc
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, params: dict) -> str:
        url = f"{BASE}/{path}?{urlencode(params)}"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def search(self, *, target: str, query: str, display: int = 20) -> str:
        params = {"OC": self.oc, "target": target, "type": "XML",
                  "query": query, "display": display}
        return self._get("lawSearch.do", params)

    def fetch(self, *, target: str, id: str) -> str:
        params = {"OC": self.oc, "target": target, "type": "XML",
                  _ID_PARAM[target]: id}
        return self._get("lawService.do", params)
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_law_client.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/ingest/ pipelines/tests/test_law_client.py
git commit -m "feat(pipelines): add law.go.kr HTTP client"
```

---

## Task 4: 실제 fixture 캡처 (네트워크, 수동 실행)

**Files:**
- Create: `pipelines/scripts/capture_fixtures.py`
- Output: `pipelines/tests/fixtures/law_주택임대차보호법.xml`, `prec_search.xml`, `prec_one.xml`

이후 파서 task들이 **추측이 아닌 실제 응답**에 대해 작성되도록, 대표 응답을 캡처해 저장한다.

- [ ] **Step 1: 캡처 스크립트 작성**

`pipelines/scripts/capture_fixtures.py`:
```python
"""실제 OPEN API를 호출해 파서 테스트용 fixture를 저장한다.

실행: cd pipelines && uv run python scripts/capture_fixtures.py
필요: pipelines/.env 의 LAW_API_OC
"""
from pathlib import Path

from pipelines.config import Config
from pipelines.ingest.law_client import LawClient

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def main() -> None:
    cfg = Config.from_env()
    client = LawClient(oc=cfg.oc)
    FIX.mkdir(parents=True, exist_ok=True)

    # 1) 법령 본문: 주택임대차보호법
    search = client.search(target="law", query="주택임대차보호법", display=1)
    (FIX / "law_search.xml").write_text(search, encoding="utf-8")
    mst = _first_tag(search, "법령일련번호") or _first_tag(search, "MST")
    if mst:
        law = client.fetch(target="law", id=mst)
        (FIX / "law_주택임대차보호법.xml").write_text(law, encoding="utf-8")

    # 2) 판례 검색 + 본문 1건
    prec_search = client.search(target="prec", query="임대차 보증금 반환", display=5)
    (FIX / "prec_search.xml").write_text(prec_search, encoding="utf-8")
    pid = _first_tag(prec_search, "판례일련번호")
    if pid:
        prec = client.fetch(target="prec", id=pid)
        (FIX / "prec_one.xml").write_text(prec, encoding="utf-8")

    print("저장된 fixture:", sorted(p.name for p in FIX.glob("*.xml")))


def _first_tag(xml_text: str, tag: str) -> str | None:
    from lxml import etree

    root = etree.fromstring(xml_text.encode("utf-8"))
    el = root.find(f".//{tag}")
    return el.text.strip() if el is not None and el.text else None


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 환경 준비**

Run:
```bash
cd pipelines && cp -n .env.example .env
```
그리고 `.env` 의 `LAW_API_OC` 를 발급받은 값으로 수정한다.
이후 셸에 로드:
```bash
cd pipelines && set -a && source .env && set +a
```

- [ ] **Step 3: 캡처 실행**

Run:
```bash
cd pipelines && set -a && source .env && set +a && uv run python scripts/capture_fixtures.py
```
Expected: `저장된 fixture: ['law_search.xml', 'law_주택임대차보호법.xml', 'prec_one.xml', 'prec_search.xml']`

- [ ] **Step 4: 실제 요소명 확인**

Run:
```bash
cd pipelines && uv run python -c "from lxml import etree; r=etree.parse('tests/fixtures/law_주택임대차보호법.xml').getroot(); print([e.tag for e in r.iter()][:40])"
```
Expected: `법령`, `기본정보`, `법령명_한글`, `조문`, `조문단위`, `조문번호`, `조문제목`, `조문내용` 등 요소 태그 목록 출력.
> 실제 태그가 Task 5의 가정과 다르면, Task 5의 XPath를 캡처된 태그에 맞춰 수정한다(파서 테스트가 fixture 기반이므로 자동으로 드러난다).

- [ ] **Step 5: Commit (fixture 포함)**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add -f pipelines/tests/fixtures/*.xml pipelines/scripts/capture_fixtures.py
git commit -m "test(pipelines): capture real law.go.kr API fixtures"
```
> fixture는 `data/`가 아니라 `tests/`에 있으므로 gitignore 영향 없음. `-f`는 안전장치.

---

## Task 5: 법령 파서 (XML → 조문 구조)

**Files:**
- Create: `pipelines/src/pipelines/ingest/law_parser.py`
- Test: `pipelines/tests/test_law_parser.py`

캡처된 `law_주택임대차보호법.xml` 에 대해 조문 단위 추출을 검증한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_law_parser.py`:
```python
from pipelines.ingest.law_parser import parse_law


def test_parses_law_name_and_articles(fixtures_dir):
    xml = (fixtures_dir / "law_주택임대차보호법.xml").read_text(encoding="utf-8")
    law = parse_law(xml)

    assert law["law_name"] == "주택임대차보호법"
    assert law["articles"], "조문이 하나 이상 추출돼야 한다"

    art = law["articles"][0]
    assert set(art.keys()) == {"article_no", "title", "text"}
    assert art["article_no"]            # 예: "제1조"
    assert isinstance(art["text"], str) and art["text"].strip()


def test_every_article_has_nonempty_text(fixtures_dir):
    xml = (fixtures_dir / "law_주택임대차보호법.xml").read_text(encoding="utf-8")
    law = parse_law(xml)
    assert all(a["text"].strip() for a in law["articles"])
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_law_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.ingest.law_parser'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/ingest/law_parser.py`:
```python
"""국가법령정보센터 lawService.do(target=law) XML 파서.

문서화된 요소명을 사용한다: 법령명_한글, 조문단위, 조문번호, 조문제목, 조문내용, 항.
Task 4 Step 4에서 실제 태그를 확인하고, 다르면 아래 상수를 조정한다.
"""
from lxml import etree

_NAME = "법령명_한글"
_UNIT = "조문단위"
_NO = "조문번호"
_TITLE = "조문제목"
_CONTENT = "조문내용"


def parse_law(xml_text: str) -> dict:
    root = etree.fromstring(xml_text.encode("utf-8"))

    name_el = root.find(f".//{_NAME}")
    law_name = (name_el.text or "").strip() if name_el is not None else ""

    articles = []
    for unit in root.iter(_UNIT):
        no = _text(unit.find(_NO))
        if not no:
            continue
        title = _text(unit.find(_TITLE))
        # 조문내용 + 모든 항 텍스트를 합친다
        parts = [t.strip() for t in unit.itertext() if t and t.strip()]
        text = "\n".join(dict.fromkeys(parts))  # 순서 유지 중복 제거
        articles.append({
            "article_no": _normalize_no(no),
            "title": title,
            "text": text,
        })
    return {"law_name": law_name, "articles": articles}


def _text(el) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def _normalize_no(no: str) -> str:
    no = no.strip()
    return no if no.startswith("제") else f"제{no}조"
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_law_parser.py -v`
Expected: PASS (2 passed)
> 실패 시 Task 4 Step 4의 실제 태그 출력과 대조해 `_UNIT`/`_NO`/`_CONTENT` 상수를 맞춘다.

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/ingest/law_parser.py pipelines/tests/test_law_parser.py
git commit -m "feat(pipelines): add 법령 XML parser"
```

---

## Task 6: 판례 파서 (XML → 판시사항/판결요지)

**Files:**
- Create: `pipelines/src/pipelines/ingest/prec_parser.py`
- Test: `pipelines/tests/test_prec_parser.py`

캡처된 `prec_one.xml` 에 대해 검증한다. 판례 본문은 `판시사항`, `판결요지`, `판례내용`, `사건명`, `사건번호`, `선고일자`, `법원명` 요소를 가진다.

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_prec_parser.py`:
```python
from pipelines.ingest.prec_parser import parse_prec


def test_parses_case_metadata_and_sections(fixtures_dir):
    xml = (fixtures_dir / "prec_one.xml").read_text(encoding="utf-8")
    prec = parse_prec(xml)

    assert prec["case_name"]                # 사건명
    assert prec["case_no"]                  # 사건번호
    assert prec["court"]                    # 법원명
    # 판시사항/판결요지 중 최소 하나는 비어있지 않아야 한다
    assert (prec["holding_summary"].strip() or prec["judgment_summary"].strip())


def test_sections_are_strings(fixtures_dir):
    xml = (fixtures_dir / "prec_one.xml").read_text(encoding="utf-8")
    prec = parse_prec(xml)
    for key in ("holding_summary", "judgment_summary", "body"):
        assert isinstance(prec[key], str)
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_prec_parser.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.ingest.prec_parser'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/ingest/prec_parser.py`:
```python
"""국가법령정보센터 lawService.do(target=prec) XML 파서."""
from lxml import etree


def parse_prec(xml_text: str) -> dict:
    root = etree.fromstring(xml_text.encode("utf-8"))
    return {
        "case_name": _t(root, "사건명"),
        "case_no": _t(root, "사건번호"),
        "court": _t(root, "법원명"),
        "decided_on": _t(root, "선고일자"),
        "holding_summary": _t(root, "판시사항"),
        "judgment_summary": _t(root, "판결요지"),
        "body": _t(root, "판례내용"),
    }


def _t(root, tag: str) -> str:
    el = root.find(f".//{tag}")
    if el is None:
        return ""
    # 일부 요소는 HTML/줄바꿈을 포함 → 모든 하위 텍스트 결합
    return "".join(el.itertext()).strip()
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_prec_parser.py -v`
Expected: PASS (2 passed)
> 실패 시 실제 태그명을 확인:
> `uv run python -c "from lxml import etree; print([e.tag for e in etree.parse('tests/fixtures/prec_one.xml').getroot().iter()][:30])"`

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/ingest/prec_parser.py pipelines/tests/test_prec_parser.py
git commit -m "feat(pipelines): add 판례 XML parser"
```

---

## Task 7: 수집 오케스트레이션 → data/raw

**Files:**
- Create: `pipelines/src/pipelines/ingest/fetch_corpus.py`
- Test: `pipelines/tests/test_fetch_corpus.py`

대상 법령(주택임대차보호법, 민법) 본문과 보증금 반환 판례를 수집해 `data/raw/`에 구조화 JSON으로 저장한다. 네트워크 의존 부분(클라이언트)은 주입해 테스트한다.

대상 목록:
- 법령: `주택임대차보호법`, `민법`
- 판례 검색어: `임대차 보증금 반환`, `임차보증금 반환`, `보증금 반환 동시이행`

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_fetch_corpus.py`:
```python
import json

from pipelines.ingest.fetch_corpus import collect


class StubClient:
    """fixture XML을 그대로 돌려주는 가짜 클라이언트."""
    def __init__(self, fixtures_dir):
        self.f = fixtures_dir

    def search(self, *, target, query, display=20):
        name = "law_search.xml" if target == "law" else "prec_search.xml"
        return (self.f / name).read_text(encoding="utf-8")

    def fetch(self, *, target, id):
        name = "law_주택임대차보호법.xml" if target == "law" else "prec_one.xml"
        return (self.f / name).read_text(encoding="utf-8")


def test_collect_writes_law_and_prec_json(tmp_path, fixtures_dir):
    client = StubClient(fixtures_dir)
    collect(client=client, out_dir=tmp_path,
            law_queries=["주택임대차보호법"],
            prec_queries=["임대차 보증금 반환"])

    laws = list((tmp_path / "law").glob("*.json"))
    precs = list((tmp_path / "prec").glob("*.json"))
    assert laws and precs

    law = json.loads(laws[0].read_text(encoding="utf-8"))
    assert law["law_name"] == "주택임대차보호법"
    assert law["articles"]
    assert law["source_url"].startswith("https://www.law.go.kr")
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_fetch_corpus.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.ingest.fetch_corpus'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/ingest/fetch_corpus.py`:
```python
"""대상 법령·판례를 수집해 data/raw/{law,prec}/*.json 으로 저장한다."""
import json
import re
from pathlib import Path

from lxml import etree

from ..config import Config
from .law_client import LawClient
from .law_parser import parse_law
from .prec_parser import parse_prec

LAW_QUERIES = ["주택임대차보호법", "민법"]
PREC_QUERIES = ["임대차 보증금 반환", "임차보증금 반환", "보증금 반환 동시이행"]

_LAW_URL = "https://www.law.go.kr/법령/{name}"
_PREC_URL = "https://www.law.go.kr/판례/{id}"


def collect(*, client, out_dir: Path, law_queries=None, prec_queries=None) -> None:
    out_dir = Path(out_dir)
    (out_dir / "law").mkdir(parents=True, exist_ok=True)
    (out_dir / "prec").mkdir(parents=True, exist_ok=True)

    for q in (law_queries or LAW_QUERIES):
        search_xml = client.search(target="law", query=q, display=1)
        mst = _first(search_xml, "법령일련번호") or _first(search_xml, "MST")
        if not mst:
            continue
        law = parse_law(client.fetch(target="law", id=mst))
        law["source_url"] = _LAW_URL.format(name=law["law_name"])
        _write(out_dir / "law" / f"{_slug(law['law_name'])}.json", law)

    seen: set[str] = set()
    for q in (prec_queries or PREC_QUERIES):
        search_xml = client.search(target="prec", query=q, display=20)
        for pid in _all(search_xml, "판례일련번호"):
            if pid in seen:
                continue
            seen.add(pid)
            prec = parse_prec(client.fetch(target="prec", id=pid))
            prec["prec_id"] = pid
            prec["source_url"] = _PREC_URL.format(id=pid)
            _write(out_dir / "prec" / f"{pid}.json", prec)


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _first(xml_text: str, tag: str) -> str | None:
    root = etree.fromstring(xml_text.encode("utf-8"))
    el = root.find(f".//{tag}")
    return el.text.strip() if el is not None and el.text else None


def _all(xml_text: str, tag: str) -> list[str]:
    root = etree.fromstring(xml_text.encode("utf-8"))
    return [e.text.strip() for e in root.iter(tag) if e.text and e.text.strip()]


def _slug(s: str) -> str:
    return re.sub(r"\s+", "_", s.strip())


def main() -> None:
    cfg = Config.from_env()
    cfg.ensure_dirs()
    collect(client=LawClient(oc=cfg.oc), out_dir=cfg.raw_dir)
    print(f"수집 완료 → {cfg.raw_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_fetch_corpus.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 실제 수집 실행 (네트워크)**

Run:
```bash
cd pipelines && set -a && source .env && set +a && uv run python -m pipelines.ingest.fetch_corpus
```
Expected: `수집 완료 → .../data/raw`. `data/raw/law/*.json`, `data/raw/prec/*.json` 생성. 판례 수십 건.

- [ ] **Step 6: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/ingest/fetch_corpus.py pipelines/tests/test_fetch_corpus.py
git commit -m "feat(pipelines): add corpus collection orchestration"
```

---

## Task 8: 텍스트 정규화

**Files:**
- Create: `pipelines/src/pipelines/clean/__init__.py` (빈 파일)
- Create: `pipelines/src/pipelines/clean/normalize.py`
- Test: `pipelines/tests/test_normalize.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_normalize.py`:
```python
from pipelines.clean.normalize import normalize_text


def test_collapses_whitespace():
    assert normalize_text("가  나\t다") == "가 나 다"


def test_strips_and_normalizes_newlines():
    assert normalize_text("\n\n가\n\n\n나\n") == "가\n나"


def test_removes_soft_hyphen_and_nbsp():
    assert normalize_text("가­나 다") == "가나 다"


def test_empty_stays_empty():
    assert normalize_text("   ") == ""
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.clean.normalize'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/clean/__init__.py`: (빈 파일)

`pipelines/src/pipelines/clean/normalize.py`:
```python
import re

_SOFT_HYPHEN = "­"


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace(_SOFT_HYPHEN, "")
    text = text.replace(" ", " ")            # nbsp → space
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 줄 단위로 내부 공백 축약 + 빈 줄 제거
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_normalize.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/clean/ pipelines/tests/test_normalize.py
git commit -m "feat(pipelines): add text normalization"
```

---

## Task 9: 구조 인지 청킹 → data/chunks/chunks.jsonl

**Files:**
- Create: `pipelines/src/pipelines/chunk/__init__.py` (빈 파일)
- Create: `pipelines/src/pipelines/chunk/chunker.py`
- Test: `pipelines/tests/test_chunker.py`

`data/raw/`의 법령·판례 JSON을 읽어 스펙 5.3 청크로 변환한다. 법령=조문 단위, 판례=판시사항·판결요지 단위.

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_chunker.py`:
```python
from pipelines.chunk.chunker import chunk_law, chunk_prec


def test_chunk_law_one_chunk_per_article():
    law = {
        "law_name": "주택임대차보호법",
        "source_url": "https://www.law.go.kr/법령/주택임대차보호법",
        "articles": [
            {"article_no": "제3조의2", "title": "보증금의 회수", "text": "임차인은 ..."},
            {"article_no": "제4조", "title": "임대차기간", "text": "기간을 정하지 ..."},
        ],
    }
    chunks = chunk_law(law, date="2023-07-19")
    assert len(chunks) == 2
    c = chunks[0]
    assert c["source_type"] == "법령"
    assert c["title"] == "주택임대차보호법 제3조의2(보증금의 회수)"
    assert c["ref"] == "제3조의2"
    assert "임차인은" in c["text"]
    assert c["id"] == "law-주택임대차보호법-제3조의2"


def test_chunk_prec_splits_sections():
    prec = {
        "prec_id": "98765",
        "case_name": "보증금반환",
        "case_no": "2020다12345",
        "court": "대법원",
        "decided_on": "20210115",
        "holding_summary": "임대차 종료 후 ...",
        "judgment_summary": "동시이행 관계에 ...",
        "body": "...",
        "source_url": "https://www.law.go.kr/판례/98765",
    }
    chunks = chunk_prec(prec)
    refs = {c["ref"] for c in chunks}
    assert refs == {"판시사항", "판결요지"}
    for c in chunks:
        assert c["source_type"] == "판례"
        assert c["title"].startswith("대법원 2020다12345")
        assert c["date"] == "2021-01-15"


def test_chunk_prec_skips_empty_sections():
    prec = {
        "prec_id": "1", "case_name": "x", "case_no": "2020다1", "court": "대법원",
        "decided_on": "20210115", "holding_summary": "", "judgment_summary": "내용",
        "body": "", "source_url": "u",
    }
    chunks = chunk_prec(prec)
    assert len(chunks) == 1 and chunks[0]["ref"] == "판결요지"
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_chunker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.chunk.chunker'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/chunk/__init__.py`: (빈 파일)

`pipelines/src/pipelines/chunk/chunker.py`:
```python
"""법령·판례 JSON → Chunk(jsonl). 구조 인지 청킹."""
import json
from pathlib import Path

from ..clean.normalize import normalize_text
from ..schema import Chunk, make_chunk


def chunk_law(law: dict, *, date: str) -> list[Chunk]:
    name = law["law_name"]
    url = law.get("source_url", "")
    chunks: list[Chunk] = []
    for art in law["articles"]:
        no = art["article_no"]
        title = art.get("title", "")
        head = f"{name} {no}" + (f"({title})" if title else "")
        chunks.append(make_chunk(
            id=f"law-{name}-{no}",
            text=normalize_text(art["text"]),
            source_type="법령",
            title=head,
            ref=no,
            url=url,
            date=date,
        ))
    return chunks


def chunk_prec(prec: dict) -> list[Chunk]:
    title = f"{prec['court']} {prec['case_no']} {prec.get('case_name', '')}".strip()
    date = _fmt_date(prec.get("decided_on", ""))
    url = prec.get("source_url", "")
    pid = prec.get("prec_id", prec.get("case_no", ""))

    chunks: list[Chunk] = []
    for ref, key in (("판시사항", "holding_summary"), ("판결요지", "judgment_summary")):
        text = normalize_text(prec.get(key, ""))
        if not text:
            continue
        chunks.append(make_chunk(
            id=f"prec-{pid}-{ref}",
            text=text,
            source_type="판례",
            title=title,
            ref=ref,
            url=url,
            date=date,
        ))
    return chunks


def _fmt_date(yyyymmdd: str) -> str:
    s = yyyymmdd.strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def build_all(raw_dir: Path, out_path: Path, *, law_date: str = "") -> int:
    """raw_dir의 모든 JSON → out_path(jsonl). 작성된 청크 수 반환."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for p in sorted((raw_dir / "law").glob("*.json")):
            law = json.loads(p.read_text(encoding="utf-8"))
            for c in chunk_law(law, date=law_date):
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
        for p in sorted((raw_dir / "prec").glob("*.json")):
            prec = json.loads(p.read_text(encoding="utf-8"))
            for c in chunk_prec(prec):
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
    return n


def main() -> None:
    from ..config import Config

    cfg = Config.from_env()
    cfg.ensure_dirs()
    out = cfg.chunks_dir / "chunks.jsonl"
    n = build_all(cfg.raw_dir, out)
    print(f"청크 {n}개 → {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_chunker.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 실제 청킹 실행**

Run:
```bash
cd pipelines && set -a && source .env && set +a && uv run python -m pipelines.chunk.chunker
```
Expected: `청크 N개 → .../data/chunks/chunks.jsonl` (N은 수백 단위)

- [ ] **Step 6: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/chunk/ pipelines/tests/test_chunker.py
git commit -m "feat(pipelines): add structure-aware chunking"
```

---

## Task 10: 임베딩 래퍼 (bge-m3)

**Files:**
- Create: `pipelines/src/pipelines/index/__init__.py` (빈 파일)
- Create: `pipelines/src/pipelines/index/embedder.py`
- Test: `pipelines/tests/test_embedder.py`

`Embedder`는 인코딩 함수를 주입받아 단위 테스트 가능하게 하고, 기본은 bge-m3(MPS)를 지연 로딩한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_embedder.py`:
```python
import pytest

from pipelines.index.embedder import Embedder


def test_embed_uses_injected_encoder():
    calls = {}

    def fake_encode(texts):
        calls["texts"] = list(texts)
        return [[0.1, 0.2], [0.3, 0.4]]

    emb = Embedder(encode_fn=fake_encode)
    vecs = emb.embed(["가", "나"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
    assert calls["texts"] == ["가", "나"]


def test_embed_empty_returns_empty():
    emb = Embedder(encode_fn=lambda t: [])
    assert emb.embed([]) == []


@pytest.mark.slow
def test_real_bge_m3_dimension():
    emb = Embedder()  # 실제 모델 로딩
    vecs = emb.embed(["보증금 반환 청구"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 1024     # bge-m3 dense 차원
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_embedder.py -v -m "not slow"`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.index.embedder'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/index/__init__.py`: (빈 파일)

`pipelines/src/pipelines/index/embedder.py`:
```python
"""bge-m3 임베딩 래퍼. encode_fn 주입으로 테스트 가능."""
from typing import Callable, Optional

MODEL_NAME = "BAAI/bge-m3"


class Embedder:
    def __init__(self, encode_fn: Optional[Callable[[list[str]], list]] = None,
                 model_name: str = MODEL_NAME):
        self._encode_fn = encode_fn
        self._model_name = model_name
        self._model = None

    def _lazy_encode(self, texts: list[str]) -> list:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import torch

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self._model = SentenceTransformer(self._model_name, device=device)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed(self, texts: list[str]) -> list:
        if not texts:
            return []
        fn = self._encode_fn or self._lazy_encode
        return fn(texts)
```

- [ ] **Step 4: 통과 확인 (빠른 테스트)**

Run: `cd pipelines && uv run pytest tests/test_embedder.py -v -m "not slow"`
Expected: PASS (2 passed, 1 deselected)

- [ ] **Step 5: 실제 모델 스모크 테스트 (느림, bge-m3 최초 다운로드 ~2GB)**

Run: `cd pipelines && uv run pytest tests/test_embedder.py -v -m slow`
Expected: PASS (1 passed) — 차원 1024 확인. 최초 실행은 모델 다운로드로 수 분 소요.

- [ ] **Step 6: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/index/embedder.py pipelines/tests/test_embedder.py
git commit -m "feat(pipelines): add bge-m3 embedder wrapper"
```

---

## Task 11: Chroma 색인 구축

**Files:**
- Create: `pipelines/src/pipelines/index/build_index.py`
- Test: `pipelines/tests/test_build_index.py`

청크 jsonl을 읽어 임베딩 후 Chroma 컬렉션에 저장한다. 임베딩은 우리가 직접 계산해 Chroma에 넘긴다(Chroma 기본 임베더 미사용).

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_build_index.py`:
```python
import json

from pipelines.index.build_index import build_index, COLLECTION


def _write_chunks(path, chunks):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def test_build_index_adds_all_chunks(tmp_path):
    chunks_path = tmp_path / "chunks.jsonl"
    _write_chunks(chunks_path, [
        {"id": "law-1", "text": "임차인은 보증금을 ...", "source_type": "법령",
         "title": "주택임대차보호법 제3조의2", "ref": "제3조의2", "url": "u", "date": "2023-07-19"},
        {"id": "prec-1", "text": "동시이행 관계 ...", "source_type": "판례",
         "title": "대법원 2020다1", "ref": "판결요지", "url": "u", "date": "2021-01-15"},
    ])

    # 결정적 가짜 임베딩(텍스트 길이 기반 2차원)
    def fake_encode(texts):
        return [[float(len(t)), 1.0] for t in texts]

    count = build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma",
                        encode_fn=fake_encode)
    assert count == 2

    import chromadb
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = client.get_collection(COLLECTION)
    assert col.count() == 2

    got = col.get(ids=["law-1"], include=["metadatas", "documents"])
    assert got["documents"][0].startswith("임차인은")
    assert got["metadatas"][0]["source_type"] == "법령"


def test_build_index_is_idempotent(tmp_path):
    chunks_path = tmp_path / "chunks.jsonl"
    _write_chunks(chunks_path, [
        {"id": "law-1", "text": "a", "source_type": "법령",
         "title": "t", "ref": "r", "url": "u", "date": "2023-01-01"},
    ])
    fn = lambda texts: [[1.0, 0.0] for _ in texts]
    build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma", encode_fn=fn)
    build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma", encode_fn=fn)

    import chromadb
    col = chromadb.PersistentClient(path=str(tmp_path / "chroma")).get_collection(COLLECTION)
    assert col.count() == 1     # 중복 삽입 없음(upsert)
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_build_index.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.index.build_index'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/index/build_index.py`:
```python
"""청크 jsonl → Chroma 색인. 임베딩은 직접 계산해 전달."""
import json
from pathlib import Path

import chromadb

from .embedder import Embedder

COLLECTION = "jeonse_deposit"
_BATCH = 64


def build_index(*, chunks_path: Path, chroma_dir: Path, encode_fn=None) -> int:
    chunks = [json.loads(ln) for ln in Path(chunks_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not chunks:
        return 0

    embedder = Embedder(encode_fn=encode_fn)
    chroma_dir = Path(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    for i in range(0, len(chunks), _BATCH):
        batch = chunks[i:i + _BATCH]
        embeddings = embedder.embed([c["text"] for c in batch])
        col.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=embeddings,
            metadatas=[{k: c[k] for k in ("source_type", "title", "ref", "url", "date")}
                       for c in batch],
        )
    return len(chunks)


def main() -> None:
    from ..config import Config

    cfg = Config.from_env()
    cfg.ensure_dirs()
    n = build_index(chunks_path=cfg.chunks_dir / "chunks.jsonl", chroma_dir=cfg.chroma_dir)
    print(f"색인 {n}개 청크 → {cfg.chroma_dir} (collection={COLLECTION})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_build_index.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 실제 색인 구축 (실제 bge-m3 사용, 느림)**

Run:
```bash
cd pipelines && set -a && source .env && set +a && uv run python -m pipelines.index.build_index
```
Expected: `색인 N개 청크 → .../data/chroma (collection=jeonse_deposit)`

- [ ] **Step 6: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/index/build_index.py pipelines/tests/test_build_index.py
git commit -m "feat(pipelines): add Chroma index builder"
```

---

## Task 12: 검색 CLI (엔드투엔드 스모크 검증)

**Files:**
- Create: `pipelines/src/pipelines/cli/__init__.py` (빈 파일)
- Create: `pipelines/src/pipelines/cli/query.py`
- Test: `pipelines/tests/test_query.py`

질의를 임베딩해 Chroma에서 top-k를 검색해 출력한다. 계획 2의 `packages/rag` 검색 로직의 원형이 된다.

- [ ] **Step 1: 실패하는 테스트 작성**

`pipelines/tests/test_query.py`:
```python
from pipelines.index.build_index import build_index
from pipelines.cli.query import search


def test_search_returns_topk_with_metadata(tmp_path):
    import json
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {"id": "a", "text": "보증금 반환 청구", "source_type": "법령",
         "title": "주택임대차보호법 제3조의2", "ref": "제3조의2", "url": "u1", "date": "2023-07-19"},
        {"id": "b", "text": "임대차 기간", "source_type": "법령",
         "title": "주택임대차보호법 제4조", "ref": "제4조", "url": "u2", "date": "2023-07-19"},
    ]
    with chunks_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 텍스트에 '보증금' 포함 시 첫 축을 크게 → 질의와 가깝게
    def fake_encode(texts):
        return [[1.0, 0.0] if "보증금" in t else [0.0, 1.0] for t in texts]

    build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma", encode_fn=fake_encode)

    results = search("보증금을 못 받았어요", chroma_dir=tmp_path / "chroma",
                     encode_fn=fake_encode, k=1)
    assert len(results) == 1
    assert results[0]["id"] == "a"
    assert results[0]["title"].startswith("주택임대차보호법")
    assert "보증금" in results[0]["text"]
```

- [ ] **Step 2: 실패 확인**

Run: `cd pipelines && uv run pytest tests/test_query.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pipelines.cli.query'`

- [ ] **Step 3: 구현**

`pipelines/src/pipelines/cli/__init__.py`: (빈 파일)

`pipelines/src/pipelines/cli/query.py`:
```python
"""검색 스모크 CLI: 질의 → top-k 청크."""
import sys
from pathlib import Path

import chromadb

from ..index.build_index import COLLECTION
from ..index.embedder import Embedder


def search(query: str, *, chroma_dir: Path, encode_fn=None, k: int = 6) -> list[dict]:
    embedder = Embedder(encode_fn=encode_fn)
    qvec = embedder.embed([query])[0]
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_collection(COLLECTION)
    res = col.query(query_embeddings=[qvec], n_results=k,
                    include=["documents", "metadatas", "distances"])
    out = []
    for id_, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                    res["metadatas"][0], res["distances"][0]):
        out.append({"id": id_, "text": doc, "distance": dist, **meta})
    return out


def main() -> None:
    from ..config import Config

    if len(sys.argv) < 2:
        print('사용법: uv run python -m pipelines.cli.query "질문"')
        raise SystemExit(1)
    cfg = Config.from_env()
    results = search(" ".join(sys.argv[1:]), chroma_dir=cfg.chroma_dir)
    for i, r in enumerate(results, 1):
        print(f"[{i}] ({r['source_type']}) {r['title']} · dist={r['distance']:.3f}")
        print(f"    {r['text'][:120]}...")
        print(f"    출처: {r['url']}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `cd pipelines && uv run pytest tests/test_query.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: 실제 검색 스모크 (네트워크/모델, 색인 완료 후)**

Run:
```bash
cd pipelines && set -a && source .env && set +a && uv run python -m pipelines.cli.query "전세 보증금을 집주인이 안 돌려줘요"
```
Expected: 주택임대차보호법 보증금 관련 조문/판례가 상위에 출력됨(제3조의2 등). 출처 URL 표시.

- [ ] **Step 6: 전체 테스트 실행**

Run: `cd pipelines && uv run pytest -m "not slow" -q`
Expected: 모든 빠른 테스트 PASS.

- [ ] **Step 7: Commit**

```bash
cd /Users/fujii0711/Claude/privateLLM
git add pipelines/src/pipelines/cli/ pipelines/tests/test_query.py
git commit -m "feat(pipelines): add retrieval smoke-test CLI"
```

---

## 완료 기준 (Definition of Done)

- [ ] `uv run pytest -m "not slow"` 전체 통과.
- [ ] `data/raw/` 에 법령 2건 + 판례 수십 건 JSON 존재.
- [ ] `data/chunks/chunks.jsonl` 에 수백 개 청크(법령 조문 + 판례 판시사항/판결요지) 존재.
- [ ] `data/chroma/` 에 `jeonse_deposit` 컬렉션 존재, 청크 수와 일치.
- [ ] `python -m pipelines.cli.query "보증금"` 가 보증금 반환 관련 법조항·판례를 상위에 반환.

이 시점에서 **검색 가능한 도메인 인덱스**가 완성된다 → 계획 2(RAG 베이스라인 챗봇)의 입력.

---

## 후속 계획으로의 인계 (계획 2 입력)

- 청크 스키마: `pipelines/src/pipelines/schema.py` 의 `Chunk` (계획 2 `packages/rag`가 동일 형태 재사용).
- 색인 위치/컬렉션명: `data/chroma`, `COLLECTION="jeonse_deposit"`.
- 검색 함수 원형: `pipelines/src/pipelines/cli/query.py:search` → 계획 2에서 `packages/rag`로 승격·재사용.
- 임베딩 모델: `BAAI/bge-m3`(1024차원, cosine) — 계획 2 질의 임베딩과 반드시 동일 모델 사용.
