"""라이브 평가 실행: 실제 retriever + MlxLLM로 평가셋을 돌려 리포트를 저장한다.

실행: uv run --package eval python -m eval.cli [--label baseline]
"""
import json
import sys
from pathlib import Path

from api.llm import MlxLLM
from api.settings import Settings
from rag.retriever import Retriever

from .dataset import load_eval_set
from .report import aggregate
from .runner import run_item

_EVAL_SET = Path(__file__).resolve().parents[2] / "eval_set.jsonl"
_REPO_ROOT = Path(__file__).resolve().parents[4]
_OUT_DIR = _REPO_ROOT / "data" / "eval_runs"


def main() -> None:
    label = "baseline"
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]

    settings = Settings.from_env()
    retriever = Retriever(settings.rag)
    llm = MlxLLM(settings.mlx_model)
    judge_fn = lambda prompt: "".join(llm.stream(
        [{"role": "user", "content": prompt}], max_tokens=16, temperature=0.0))

    items = load_eval_set(_EVAL_SET)
    results = []
    for i, item in enumerate(items, 1):
        res = run_item(item, retriever=retriever, llm=llm,
                       judge_fn=judge_fn, top_k=settings.rag.top_k)
        results.append(res)
        print(f"[{i}/{len(items)}] {item.id} hit={res.retrieval_hit} "
              f"cite={res.metrics['has_citation']} ground={res.groundedness:.2f}")

    agg = aggregate(results)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = _OUT_DIR / f"{label}.json"
    out.write_text(json.dumps({
        "label": label, "summary": agg,
        "items": [{"id": r.id, "retrieval_hit": r.retrieval_hit,
                   "metrics": r.metrics, "groundedness": r.groundedness,
                   "answer": r.answer} for r in results],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== {label} 요약 ===")
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print(f"저장: {out}")


if __name__ == "__main__":
    main()
