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
