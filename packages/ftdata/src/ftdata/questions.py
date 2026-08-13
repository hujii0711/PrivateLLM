"""질문 풀 로더 (평가셋과 disjoint한 보증금 반환 질문).
--> Path(__file__).parents[2] 경로 계산 방식, JSONL 형식 설명, 함수 Args/Returns 문서화

이 모듈은 파인튜닝(Fine-Tuning)에 사용할 질문 목록을
JSONL 파일에서 불러오는 역할을 합니다.

평가(eval)에 사용된 질문과 겹치지 않는(disjoint) 질문들만
별도로 모아둔 'question_pool.jsonl' 파일을 읽어 반환합니다.
"""

import json
from pathlib import Path

# 질문 풀 파일 경로를 자동으로 계산합니다.
# Path(__file__) → 현재 이 파이썬 파일의 경로
# .parents[2]    → 두 단계 위의 디렉토리 (패키지 루트)
# / "question_pool.jsonl" → 그 안의 JSONL 파일
_POOL = Path(__file__).resolve().parents[2] / "question_pool.jsonl"


def load_questions(path: Path = _POOL) -> list[str]:
    """질문 풀 파일에서 질문 문자열 목록을 읽어 반환합니다.

    Args:
        path: 질문 풀 JSONL 파일 경로. 기본값은 패키지 루트의 question_pool.jsonl.

    Returns:
        질문 문자열들의 리스트. 예: ["보증금 반환 기한은?", "임대차 계약 해지 절차는?", ...]

    JSONL 형식 예시 (한 줄 = 하나의 JSON 객체):
        {"question": "보증금을 돌려받으려면 어떻게 해야 하나요?"}
        {"question": "전세 계약 만료 후 집주인이 보증금을 안 주면?"}
    """
    out = []  # 결과를 담을 빈 리스트

    # 파일을 UTF-8로 읽고, 줄 단위로 순회합니다.
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():  # 빈 줄(공백만 있는 줄)은 건너뜁니다.
            # json.loads()로 JSON 문자열을 파이썬 딕셔너리로 변환한 뒤,
            # "question" 키의 값(질문 텍스트)만 꺼내 리스트에 추가합니다.
            out.append(json.loads(line)["question"])
    return out
