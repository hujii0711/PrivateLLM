privateLLM은 **uv workspace(모노레포)** 구조이고, `pyproject.toml`이 여러 개 계층으로 나뉘어 있습니다. 각 파일의 역할을 정리하면 다음과 같습니다.

## 1. 루트 [pyproject.toml](pyproject.toml) — 워크스페이스 정의

```toml
[tool.uv.workspace]
members = ["pipelines", "packages/*", "apps/*"]
exclude = ["apps/web"]
```

- **유일한 역할**: uv 워크스페이스의 멤버를 선언. 자기 자신은 패키지가 아니고, 하위 멤버들을 묶어주는 "오케스트레이터".
- `members`로 `pipelines`, `packages/*`(rag·finetune·eval·ftdata), `apps/*`(api)를 모두 한 워크스페이스로 관리 → 단일 락파일·단일 가상환경 공유.
- `apps/web`은 Python 패키지가 아니라서(프론트엔드) 제외.

## 2. 멤버 패키지들 — 각자 하나의 독립 패키지

각 멤버 `pyproject.toml`은 공통적으로 다음 4가지 블록을 가집니다.

| 블록 | 역할 |
|------|------|
| `[project]` | 패키지 이름·버전·설명, `requires-python>=3.11`, 런타임 의존성 |
| `[dependency-groups] dev` | 테스트용(`pytest` 등) 개발 의존성 |
| `[tool.pytest.ini_options]` | `pythonpath=["src"]`, `testpaths=["tests"]`, `slow` 마커 |
| `[build-system]` + `[tool.hatch...]` | hatchling 빌드 백엔드, `src/<name>` 레이아웃 |

### 멤버별 차이점 (의존성 그래프)

- **[pipelines/pyproject.toml](pipelines/pyproject.toml)** — 데이터 수집/색인. 외부 라이브러리만 의존(`requests`, `lxml`, `chromadb`, `sentence-transformers`). 다른 내부 패키지에 의존 안 함.
- **[packages/rag/pyproject.toml](packages/rag/pyproject.toml)** — RAG 검색·프롬프트·인용 코어. `chromadb`, `sentence-transformers`. 가장 하위 코어 모듈.
- **[apps/api/pyproject.toml](apps/api/pyproject.toml)** — FastAPI 백엔드. `fastapi`, `uvicorn`, `sse-starlette`, `pydantic`, `mlx-lm` + 내부 `rag`.
- **[packages/eval/pyproject.toml](packages/eval/pyproject.toml)** — 평가 하니스. 내부 `rag`, `api` 의존.
- **[packages/finetune/pyproject.toml](packages/finetune/pyproject.toml)** — QLoRA 학습 + A/B. 내부 `api`, `eval` 의존.
- **[packages/ftdata/pyproject.toml](packages/ftdata/pyproject.toml)** — 학습 데이터 빌더. 내부 `rag`, `api`, `eval` 의존.

내부 패키지를 끌어다 쓸 때는 `[tool.uv.sources]`에서 `{ workspace = true }`로 선언해 PyPI가 아닌 **워크스페이스 내 로컬 소스**를 참조하게 합니다.

## 3. 파일별 의존성 상세

각 `pyproject.toml`의 `dependencies`(런타임) / `dev`(개발) / `tool.uv.sources`(워크스페이스 내부 소스)를 정리하면 다음과 같습니다.

### 루트 [pyproject.toml](pyproject.toml)
- 런타임 의존성: 없음 (패키지가 아님, 워크스페이스 멤버만 선언)

### [pipelines/pyproject.toml](pipelines/pyproject.toml)
- **런타임**: `requests>=2.31`, `lxml>=5.0`, `chromadb>=0.5`, `sentence-transformers>=3.0`
- **dev**: `pytest>=8.0`
- **내부 소스**: 없음 (외부 라이브러리만 의존)

### [packages/rag/pyproject.toml](packages/rag/pyproject.toml)
- **런타임**: `chromadb>=0.5`, `sentence-transformers>=3.0`
- **dev**: `pytest>=8.0`
- **내부 소스**: 없음 (최하위 코어)

### [apps/api/pyproject.toml](apps/api/pyproject.toml)
- **런타임**: `fastapi>=0.115`, `uvicorn[standard]>=0.30`, `sse-starlette>=2.1`, `pydantic>=2.7`, `mlx-lm>=0.18`, `rag`
- **dev**: `pytest>=8.0`, `httpx>=0.27`
- **내부 소스**: `rag = { workspace = true }`

### [packages/eval/pyproject.toml](packages/eval/pyproject.toml)
- **런타임**: `rag`, `api`
- **dev**: `pytest>=8.0`
- **내부 소스**: `rag = { workspace = true }`, `api = { workspace = true }`

### [packages/finetune/pyproject.toml](packages/finetune/pyproject.toml)
- **런타임**: `api`, `eval`
- **dev**: `pytest>=8.0`
- **내부 소스**: `api = { workspace = true }`, `eval = { workspace = true }`

### [packages/ftdata/pyproject.toml](packages/ftdata/pyproject.toml)
- **런타임**: `rag`, `api`, `eval`
- **dev**: `pytest>=8.0`
- **내부 소스**: `rag = { workspace = true }`, `api = { workspace = true }`, `eval = { workspace = true }`

> 모든 멤버는 `requires-python = ">=3.11"`, hatchling 빌드 백엔드, `src/<name>` wheel 레이아웃을 공통으로 사용합니다.

## 의존 관계 요약

```
rag (코어)
 └─ api ── (mlx-lm, fastapi)
      ├─ eval ── (rag, api)
      │    ├─ finetune ── (api, eval)
      │    └─ ftdata ── (rag, api, eval)
      
pipelines (독립 — 데이터 파이프라인)
```

정리하면, **루트는 워크스페이스를 묶는 매니페스트**, **각 멤버는 `src/<name>` 레이아웃의 독립 패키지**이며, 내부 의존은 `workspace = true` 소스로 연결되어 하나의 환경에서 통합 관리됩니다.
