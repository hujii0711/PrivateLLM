"""
settings.py — 애플리케이션 전역 설정(Configuration) 모듈

이 파일은 API 서버가 동작할 때 필요한 설정값들을 한 곳에서 관리합니다.
환경 변수(Environment Variable)로 설정을 주입할 수 있어,
개발/운영 환경을 코드 변경 없이 전환할 수 있습니다.

【12 요소 앱(Twelve-Factor App) 원칙】
설정은 코드가 아닌 환경 변수로 관리합니다.
  - 개발 환경 : .env 파일에 값 저장
  - 운영 환경 : 서버의 환경 변수로 값 설정
"""

import os  # 환경 변수를 읽기 위한 표준 라이브러리
from dataclasses import dataclass, field  # 데이터 전용 클래스를 쉽게 만들어 주는 도구

from rag.config import RagConfig  # RAG(검색 증강 생성) 전용 설정 클래스

# ──────────────────────────────────────────────────────────
# 기본값 상수 (Constant)
# 상수는 대문자+밑줄(SNAKE_CASE)로 표기하는 파이썬 관례를 따릅니다.
# ──────────────────────────────────────────────────────────
# Hugging Face / mlx-community 에 올라온 경량화(4-bit 양자화) 모델 이름입니다.
# Qwen2.5 는 Alibaba가 공개한 오픈소스 LLM이며,
# 4bit 는 모델 가중치를 4비트로 압축해 메모리를 줄인 버전입니다.
MLX_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"


# ──────────────────────────────────────────────────────────
# Settings 데이터클래스
# @dataclass 데코레이터를 사용하면 __init__, __repr__ 등을
# 자동으로 생성해 주므로, 순수하게 필드 선언에만 집중할 수 있습니다.
# ──────────────────────────────────────────────────────────
@dataclass
class Settings:
    """API 서버 전체에서 공유되는 런타임 설정.

    Attributes:
        rag        : 벡터 DB 경로, 임베딩 모델 등 RAG 관련 설정 묶음
        mlx_model  : 로컬에서 실행할 LLM 모델 이름 (Hugging Face 경로)
        max_tokens : LLM이 한 번에 생성할 최대 토큰(단어 조각) 수
        temperature: 생성 무작위성 (0 = 결정론적, 1 = 창의적)
    """

    # field(default_factory=...) 는 가변(mutable) 기본값을 안전하게 지정하는 방법입니다.
    # 단순히 rag: RagConfig = RagConfig.from_env() 처럼 쓰면 모든 인스턴스가
    # 같은 객체를 공유하는 버그가 생기므로, default_factory 를 사용합니다.
    rag: RagConfig = field(default_factory=RagConfig.from_env)

    # 로컬 추론에 사용할 MLX 모델 이름 (기본값: 위에서 정의한 상수)
    mlx_model: str = MLX_MODEL

    # LLM 이 한 번 응답할 때 생성하는 최대 토큰 수
    # 너무 작으면 답변이 잘리고, 너무 크면 응답이 느려집니다.
    max_tokens: int = 768

    # temperature(온도): 낮을수록 일관되고 보수적인 답변,
    #                    높을수록 창의적이지만 예측 불가능한 답변이 나옵니다.
    temperature: float = 0.2

    # ──────────────────────────────────────────────────────────
    # 클래스 메서드 (Class Method)
    # @classmethod 는 인스턴스가 아닌 클래스 자체를 첫 번째 인자(cls)로 받습니다.
    # Settings.from_env() 처럼 "팩토리 메서드"로 사용됩니다.
    # ──────────────────────────────────────────────────────────
    @classmethod
    def from_env(cls) -> "Settings":
        """환경 변수에서 설정을 읽어 Settings 인스턴스를 생성합니다.

        환경 변수가 없으면 기본값(MLX_MODEL)을 사용합니다.

        사용 예:
            $ export MLX_MODEL="mlx-community/Qwen2.5-3B-Instruct-4bit"
            # 그 후 서버를 실행하면 자동으로 3B 모델을 사용합니다.
        """
        return cls(
            rag=RagConfig.from_env(),
            # os.environ.get("KEY", default) : 환경 변수 KEY가 있으면 그 값을,
            # 없으면 두 번째 인자(MLX_MODEL 상수)를 사용합니다.
            mlx_model=os.environ.get("MLX_MODEL", MLX_MODEL),
        )
