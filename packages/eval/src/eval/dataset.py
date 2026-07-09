"""
dataset.py — 평가 데이터셋(Evaluation Set) 로드 모듈

【평가셋(Evaluation Set) 이란?】
AI 모델의 성능을 객관적으로 측정하기 위해 미리 준비한 질문 목록입니다.
각 질문에는 "기대 법조항(expected_refs)"과 "필수 키워드(must_mention)" 가 함께 있어,
시스템의 검색 정확도와 답변 품질을 자동으로 평가할 수 있습니다.

【JSONL(JSON Lines) 형식이란?】
각 줄이 독립적인 JSON 객체인 파일 형식입니다.
일반 JSON 배열([...]) 과 달리, 한 줄씩 읽어 처리할 수 있어
대용량 데이터에 유리합니다.

  파일 예시 (eval_set.jsonl):
    {"id": "q1", "question": "보증금 반환 소송 방법은?", "expected_refs": ["제3조의3"], "must_mention": ["내용증명"]}
    {"id": "q2", "question": "임차권등기명령이란?", "expected_refs": ["제3조의3", "제6조"], "must_mention": []}

【평가 흐름】
  eval_set.jsonl → load_eval_set() → [EvalItem, ...] → runner.run_item() → 지표 계산
"""

import json  # JSON 파싱 표준 라이브러리
from dataclasses import dataclass, field  # 데이터클래스 선언 도구
from pathlib import Path  # 운영체제 독립적 경로 처리


# ══════════════════════════════════════════════════════════════
# EvalItem — 평가셋 1개 항목
# ══════════════════════════════════════════════════════════════
@dataclass
class EvalItem:
    """평가셋 파일(eval_set.jsonl)의 한 줄을 나타내는 데이터 클래스.

    Attributes:
        id            : 평가 항목의 고유 식별자 (예: "q1", "deposit_return_001")
        question      : 평가에 사용할 질문 텍스트
        expected_refs : 이 질문에 대한 정답 검색에 반드시 포함돼야 할 법조항 ref 목록
                        (예: ["제3조의3", "제6조"])
                        검색 단계에서 이 ref 들이 top-k 결과에 있는지 확인합니다.
        must_mention  : 최종 답변에 반드시 포함돼야 할 키워드 목록
                        (예: ["내용증명", "임차권등기"])
                        answer_metrics 에서 mention_coverage 지표 계산에 사용합니다.
    """

    id: str
    question: str

    # field(default_factory=list) : 기본값이 가변 객체(list)이므로
    # default_factory 를 사용합니다. 직접 = [] 로 쓰면 모든 인스턴스가
    # 같은 리스트 객체를 공유하는 버그가 생깁니다.
    expected_refs: list[str] = field(default_factory=list)
    must_mention: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# 파일 로더
# ══════════════════════════════════════════════════════════════
def load_eval_set(path: Path) -> list[EvalItem]:
    """JSONL 파일을 읽어 EvalItem 리스트로 반환합니다.

    빈 줄(공백만 있는 줄)은 자동으로 건너뜁니다.
    expected_refs, must_mention 이 없는 항목은 빈 리스트 기본값을 사용합니다.

    Args:
        path: eval_set.jsonl 파일의 경로

    Returns:
        EvalItem 객체 리스트 (파일의 줄 순서대로)

    Raises:
        FileNotFoundError : 파일이 존재하지 않을 때
        json.JSONDecodeError : 특정 줄의 JSON 형식이 잘못됐을 때
    """
    items: list[EvalItem] = []

    # Path(path).read_text(encoding="utf-8") : 파일 전체를 UTF-8 문자열로 읽음
    # .splitlines() : 줄바꿈 문자를 기준으로 각 줄을 리스트로 분리
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            # line.strip() 이 빈 문자열이면 (빈 줄 또는 공백만 있는 줄) 건너뜁니다.
            continue

        # json.loads(line) : JSON 문자열 → 파이썬 딕셔너리 변환
        d = json.loads(line)

        items.append(
            EvalItem(
                id=d["id"],
                question=d["question"],
                # dict.get(key, default) : 키가 없으면 기본값 반환
                expected_refs=d.get("expected_refs", []),
                must_mention=d.get("must_mention", []),
            )
        )
    return items
