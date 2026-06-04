"""채택 후보 → MLX chat JSONL 예제 + train/valid 분할."""
import json
from pathlib import Path

from rag.prompt import build_messages
from rag.types import Retrieved


def to_chat_example(question: str, hits: list[Retrieved], answer: str) -> dict:
    """서빙과 동일한 입력(system+user(근거))에 정답 답변을 붙인 MLX chat 예제."""
    messages = build_messages(question, hits)
    messages.append({"role": "assistant", "content": answer})
    return {"messages": messages}


def split_train_valid(examples: list[dict], valid_every: int = 10):
    """결정적 분할: 1-indexed로 valid_every의 배수번째를 valid로."""
    train, valid = [], []
    for i, ex in enumerate(examples):
        (valid if (i + 1) % valid_every == 0 else train).append(ex)
    return train, valid


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
