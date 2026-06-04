"""질문 풀 로더 (평가셋과 disjoint한 보증금 반환 질문)."""
import json
from pathlib import Path

_POOL = Path(__file__).resolve().parents[2] / "question_pool.jsonl"


def load_questions(path: Path = _POOL) -> list[str]:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line)["question"])
    return out
