# PrivateLLM — 주택임대차 보증금 반환 챗봇

로컬 Apple Silicon Mac에서 완전히 동작하는 **RAG 기반 법률 챗봇**입니다.  
국가법령정보센터 Open API로 법령/판례를 수집하고, 벡터 DB로 검색한 뒤, MLX 로컬 LLM으로 답변을 스트리밍합니다.

## 프로젝트 구조

```
PrivateLLM/
├── apps/
│   ├── api/        # FastAPI 백엔드 (RAG + MLX 추론)
│   └── web/        # Next.js 프론트엔드
├── packages/
│   ├── rag/        # 벡터 검색 패키지
│   ├── eval/       # 평가 패키지
│   ├── finetune/   # 파인튜닝 패키지
│   └── ftdata/     # 파인튜닝 데이터 패키지
├── pipelines/      # 데이터 수집 → 청킹 → 인덱싱 파이프라인
├── data/           # 수집·가공된 데이터 (raw / chunks / chroma)
└── pyproject.toml  # uv 워크스페이스 루트 설정
```

## 사전 요구사항

| 항목 | 버전 |
|------|------|
| macOS (Apple Silicon) | M1 이상 |
| Python | 3.11 이상 |
| Node.js | 18 이상 |
| [uv](https://docs.astral.sh/uv/) | 최신 버전 |
| 국가법령정보센터 Open API 키 | [신청](https://open.law.go.kr/) |

```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 1단계 — 데이터 파이프라인 실행 (최초 1회)

법령 데이터를 수집하고 벡터 DB를 구축합니다.

```bash
cd pipelines

# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 LAW_API_OC 값을 본인의 Open API 키로 수정
# LAW_API_OC=your_api_key

# 환경 변수 로드
set -a && source .env && set +a

# 법령 데이터 수집 → data/raw
uv run python -m pipelines.ingest.fetch_corpus

# 텍스트 청킹 → data/chunks
uv run python -m pipelines.chunk.chunker

# 벡터 인덱스 빌드 → data/chroma
uv run python -m pipelines.index.build_index
```

검색 테스트:
```bash
uv run python -m pipelines.cli.query "보증금을 못 받았어요"
```

---

## 2단계 — API 서버 실행

FastAPI 백엔드를 실행합니다. 첫 요청 시 MLX 모델이 자동으로 로드됩니다.

```bash
cd apps/api

# 의존성 설치 (uv 워크스페이스가 rag 패키지를 자동으로 연결)
uv sync

# 서버 실행 (포트: 8000)
uv run uvicorn api.main:app --reload
```

서버가 실행되면 아래 주소에서 확인할 수 있습니다:
- **API 서버**: http://localhost:8000
- **헬스 체크**: http://localhost:8000/health
- **Swagger UI**: http://localhost:8000/docs

> **참고**: 사용 모델은 기본적으로 `mlx-community/Qwen2.5-7B-Instruct-4bit`입니다.  
> 다른 모델을 사용하려면 환경 변수를 설정하세요:
> ```bash
> export MLX_MODEL="mlx-community/Qwen2.5-3B-Instruct-4bit"
> uv run uvicorn api.main:app --reload
> ```

---

## 3단계 — 웹 프론트엔드 실행

Next.js 개발 서버를 실행합니다.

```bash
cd apps/web

# 의존성 설치
npm install

# 환경 변수 설정
cp .env.local.example .env.local
# .env.local 기본값: NEXT_PUBLIC_API_BASE=http://localhost:8000
# API 서버 주소가 다르면 이 값을 수정하세요

# 개발 서버 실행 (포트: 3000)
npm run dev
```

브라우저에서 http://localhost:3000 으로 접속합니다.

---

## 전체 실행 순서 요약

```bash
# 터미널 1 — API 서버
cd apps/api && uv sync && uv run uvicorn api.main:app --reload

# 터미널 2 — 웹 프론트엔드
cd apps/web && npm install && npm run dev
```

> 데이터 파이프라인은 최초 1회만 실행하면 됩니다.  
> `data/chroma` 디렉터리가 이미 존재하면 건너뛰어도 됩니다.

---

## 테스트 실행

**파이프라인 테스트**
```bash
cd pipelines
uv run pytest            # 빠른 테스트
uv run pytest -m slow    # 모델/네트워크 포함 느린 테스트
```

**API 서버 테스트**
```bash
cd apps/api
uv run pytest
```

**웹 프론트엔드 테스트**
```bash
cd apps/web
npm test
```

---

## 코드 품질 검사

```bash
# 루트에서 전체 Python 코드 린트
uv run ruff check .

# 자동 수정
uv run ruff check --fix .
```

---

## 환경 변수 정리

| 위치 | 파일 | 변수 | 설명 |
|------|------|------|------|
| `pipelines/` | `.env` | `LAW_API_OC` | 국가법령정보센터 Open API 키 |
| `apps/web/` | `.env.local` | `NEXT_PUBLIC_API_BASE` | API 서버 주소 (기본: `http://localhost:8000`) |
| 셸 환경 변수 | — | `MLX_MODEL` | 사용할 MLX 모델명 (선택사항) |
