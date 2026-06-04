"""A/B 비교: baseline vs qlora 평가 요약 → 지표별 델타 + 마크다운."""
import json
from pathlib import Path

_METRICS = ["recall_at_k", "citation_rate", "structure_rate", "disclaimer_rate",
            "sources_rate", "mention_coverage", "groundedness"]


def load_summary(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["summary"]


def compare_runs(baseline: dict, qlora: dict) -> dict:
    out = {}
    for m in _METRICS:
        if m in baseline and m in qlora:
            out[m] = {"baseline": baseline[m], "qlora": qlora[m],
                      "delta": round(qlora[m] - baseline[m], 4)}
    return out


def to_markdown(comparison: dict) -> str:
    lines = ["| 지표 | baseline | qlora | Δ |", "|---|---|---|---|"]
    for m, v in comparison.items():
        lines.append(f"| {m} | {v['baseline']:.3f} | {v['qlora']:.3f} | {v['delta']:+.3f} |")
    return "\n".join(lines)
