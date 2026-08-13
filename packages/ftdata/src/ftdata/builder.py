"""채택 후보 → MLX chat JSONL 예제 + train/valid 분할.
--> MLX chat JSONL 형식 예시, split_train_valid 1-indexed 분할 로직, ensure_ascii=False 이유

이 모듈은 품질 필터를 통과한 후보 답변들을
MLX(Apple Silicon용 머신러닝 프레임워크)의 파인튜닝 입력 형식으로 변환하고,
train(학습)셋과 valid(검증)셋으로 나누는 역할을 합니다.

파인튜닝 데이터 형식 (MLX chat JSONL):
  한 줄 = 하나의 대화 예제 (JSON 객체)
  {"messages": [
      {"role": "system",    "content": "..."},
      {"role": "user",      "content": "..."},
      {"role": "assistant", "content": "..."}  ← 이것이 학습 정답
  ]}
"""

import json
from pathlib import Path  # 파일 경로를 OS에 상관없이 다루기 위한 표준 라이브러리

from rag.prompt import build_messages  # system+user 메시지를 조립하는 함수
from rag.types import Retrieved  # 검색 결과 한 건을 나타내는 타입


def to_chat_example(question: str, hits: list[Retrieved], answer: str) -> dict:
    """질문·검색 결과·정답 답변을 MLX chat 파인튜닝 예제 형식으로 변환합니다.

    서빙(실제 서비스) 때와 동일한 system+user 메시지를 만들고,
    마지막에 assistant 메시지(정답)를 추가합니다.
    이렇게 하면 모델이 "실제 서비스에서 어떻게 답해야 하는가"를 그대로 학습합니다.

    Args:
        question: 사용자가 입력한 질문 텍스트.
        hits:     RAG 검색으로 얻은 관련 문서(근거) 목록.
        answer:   품질 필터를 통과한 최종 정답 답변 텍스트.

    Returns:
        {"messages": [...]} 형태의 딕셔너리 (JSONL 한 줄에 해당).
    """
    # build_messages()는 [system 메시지, user 메시지(질문+근거)]를 반환합니다.
    messages = build_messages(question, hits)

    # 리스트 끝에 assistant 역할의 정답 메시지를 추가합니다.
    # 모델은 이 assistant 내용을 학습 목표(label)로 삼습니다.
    messages.append({"role": "assistant", "content": answer})

    return {"messages": messages}


def split_train_valid(examples: list[dict], valid_every: int = 10):
    """예제 목록을 train셋과 valid셋으로 분할합니다.

    분할 기준 (결정적/재현 가능):
      - 1번째부터 세어서 valid_every(기본 10)의 배수 번째 예제 → valid셋
      - 나머지 → train셋

    예) valid_every=10 이면 10번째, 20번째, 30번째, ... 예제가 valid셋이 됩니다.
    무작위(random)를 사용하지 않으므로, 실행할 때마다 동일하게 분할됩니다.

    Args:
        examples:    to_chat_example()으로 만든 예제 딕셔너리 목록.
        valid_every: 몇 개마다 하나를 valid셋으로 뺄지 결정하는 간격 (기본 10).

    Returns:
        (train, valid) 튜플:
          - train: 학습에 사용할 예제 목록.
          - valid: 검증(과적합 확인)에 사용할 예제 목록.
    """
    train, valid = [], []  # 두 버킷을 빈 리스트로 초기화

    for i, ex in enumerate(examples):  # i는 0부터 시작하는 인덱스
        # (i + 1) % valid_every == 0 → 1-indexed로 valid_every 배수인지 확인
        # 조건이 True이면 valid에, False이면 train에 넣습니다.
        (valid if (i + 1) % valid_every == 0 else train).append(ex)

    return train, valid


def write_jsonl(path: Path, rows: list[dict]) -> None:
    """딕셔너리 목록을 JSONL 형식의 파일로 저장합니다.

    JSONL(JSON Lines)이란 한 줄에 하나의 JSON 객체를 쓰는 형식입니다.
    대용량 데이터를 줄 단위로 읽고 쓸 수 있어 ML 데이터셋에서 널리 쓰입니다.

    Args:
        path: 저장할 파일 경로 (예: data/ft/train.jsonl).
        rows: 저장할 딕셔너리 목록 (각 딕셔너리가 한 줄이 됩니다).

    동작:
      - 부모 디렉토리가 없으면 자동으로 만듭니다 (mkdir parents=True).
      - 이미 같은 이름의 파일이 있으면 덮어씁니다.
      - 한국어 등 비ASCII 문자가 깨지지 않도록 ensure_ascii=False로 저장합니다.
    """
    path = Path(path)  # 문자열로 넘어온 경우도 Path 객체로 통일

    # 파일의 부모 디렉토리가 없으면 중간 디렉토리까지 모두 생성합니다.
    path.parent.mkdir(parents=True, exist_ok=True)

    # 파일을 UTF-8 쓰기 모드로 엽니다.
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            # 딕셔너리 → JSON 문자열 변환 후 줄바꿈 추가해서 한 줄씩 씁니다.
            # ensure_ascii=False: 한글 등을 \uXXXX 이스케이프 없이 그대로 저장.
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
