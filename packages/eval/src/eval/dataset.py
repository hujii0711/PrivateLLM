"""평가셋 항목 스키마 + jsonl 로더."""
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvalItem:
    id: str
    question: str
    expected_refs: list[str] = field(default_factory=list)   # 기대 법조항 ref (예: "제3조의2")
    must_mention: list[str] = field(default_factory=list)    # 답변에 포함돼야 할 키워드


def load_eval_set(path: Path) -> list[EvalItem]:
    items: list[EvalItem] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        items.append(EvalItem(
            id=d["id"], question=d["question"],
            expected_refs=d.get("expected_refs", []),
            must_mention=d.get("must_mention", []),
        ))
    return items
