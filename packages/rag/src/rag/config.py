"""
config.py — RAG 시스템 전역 설정 모듈

【RAG(Retrieval-Augmented Generation) 이란?】
LLM이 답변을 생성할 때, 미리 구축한 지식 베이스(벡터 DB)에서
관련 문서를 검색(Retrieval)해 프롬프트에 포함시키는 방식입니다.
외부 지식 없이 LLM이 "기억"에만 의존하면 오래된 정보나
존재하지 않는 내용을 꾸며내는 "환각(Hallucination)"이 발생할 수 있습니다.
RAG는 이를 방지하고 답변의 신뢰도를 높입니다.

【이 파일의 역할】
벡터 DB(ChromaDB) 접속 정보, 임베딩 모델 이름,
검색 파라미터(top_k, min_similarity) 등을 한 곳에서 관리합니다.

【중요】 색인(indexing) 단계에서 사용한 설정값과 반드시 일치해야 합니다.
색인할 때 사용한 모델과 다른 모델로 검색하면 벡터 공간이 달라져 검색 결과가 무의미해집니다.
"""

import os  # 환경 변수 읽기
from dataclasses import dataclass  # 데이터 전용 클래스 선언 도구
from pathlib import Path  # 운영체제에 독립적인 파일 경로 처리

# ──────────────────────────────────────────────────────────
# 상수(Constants) — 색인 파이프라인(Plan 1)과 반드시 동일해야 함
# ──────────────────────────────────────────────────────────

# Chroma 컬렉션(테이블) 이름.
# 색인 시 이 이름으로 문서를 저장했으므로, 검색 시에도 동일한 이름을 사용해야 합니다.
COLLECTION = "jeonse_deposit"

# 임베딩 모델 이름 (Hugging Face 식별자).
# BAAI/bge-m3 는 한국어·영어 등 다국어를 지원하는 1024차원 임베딩 모델입니다.
# 색인 시 사용한 모델과 다르면 검색이 정상 동작하지 않습니다.
MODEL_NAME = "BAAI/bge-m3"


# ──────────────────────────────────────────────────────────
# 경로 자동 계산
# ──────────────────────────────────────────────────────────
# Path(__file__) : 현재 파일(config.py)의 절대 경로
# .resolve()     : 심볼릭 링크를 해소한 실제 절대 경로
# .parents[4]    : 상위 4번째 디렉터리
#
# 파일 경로: packages/rag/src/rag/config.py
#   parents[0] = packages/rag/src/rag/
#   parents[1] = packages/rag/src/
#   parents[2] = packages/rag/
#   parents[3] = packages/
#   parents[4] = (레포 루트)  ← _REPO_ROOT
_REPO_ROOT = Path(__file__).resolve().parents[4]

# ChromaDB가 벡터를 디스크에 저장하는 기본 경로
# 레포 루트 기준: data/chroma/
_DEFAULT_CHROMA = _REPO_ROOT / "data" / "chroma"


# ══════════════════════════════════════════════════════════════
# RagConfig 데이터클래스
# @dataclass 를 사용하면 __init__, __repr__, __eq__ 를 자동 생성합니다.
# ══════════════════════════════════════════════════════════════
@dataclass
class RagConfig:
    """RAG 파이프라인 동작을 제어하는 설정값 묶음.

    Attributes:
        chroma_dir     : ChromaDB 파일이 저장된 디렉터리 경로
        collection     : ChromaDB 컬렉션(테이블) 이름
        model_name     : 임베딩 모델 이름 (색인 시와 반드시 동일해야 함)
        top_k          : 검색할 최대 문서 수 (가장 유사한 k개를 반환)
        min_similarity : 근거로 인정할 최소 코사인 유사도
                         이 값 미만이면 "관련 근거 없음"으로 처리합니다.
    """

    chroma_dir: Path = _DEFAULT_CHROMA  # 벡터 DB 저장 경로 (기본값: data/chroma)
    collection: str = COLLECTION  # 검색 대상 컬렉션 이름
    model_name: str = MODEL_NAME  # 임베딩 모델 이름

    # 유사도 검색 결과에서 반환할 최대 문서 수
    # top_k=6 이면 가장 유사한 6개 문서를 가져와 프롬프트에 포함합니다.
    top_k: int = 6

    # 코사인 유사도(Cosine Similarity) 하한값
    # 코사인 유사도 범위: -1.0(완전 반대) ~ 0.0(무관) ~ 1.0(완전 동일)
    # 0.35 미만이면 질문과 관련성이 낮다고 판단해 답변을 거부합니다.
    min_similarity: float = 0.35

    @classmethod
    def from_env(cls) -> "RagConfig":
        """환경 변수에서 설정을 읽어 RagConfig 인스턴스를 생성합니다.

        지원하는 환경 변수:
            CHROMA_DIR : ChromaDB 파일 경로 (없으면 data/chroma 기본값 사용)

        사용 예:
            $ export CHROMA_DIR="/mnt/nas/chroma"
            $ uvicorn api.main:app  # 자동으로 위 경로를 사용합니다.
        """
        chroma = os.environ.get("CHROMA_DIR")
        return cls(
            # 환경 변수가 있으면 Path 객체로 변환, 없으면 기본 경로 사용
            chroma_dir=Path(chroma) if chroma else _DEFAULT_CHROMA
        )
