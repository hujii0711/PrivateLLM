"""라이브 FT 데이터 빌드: 질문 풀 → 후보 생성 → 형식·근거 필터 → MLX chat JSONL.

실행: uv run --package ftdata python -m ftdata.cli [--k 6] [--per-q 2] [--min-ground 0.5]
출력: data/ft/train.jsonl, data/ft/valid.jsonl, data/ft/stats.json
"""
import json
import sys
from pathlib import Path

from api.llm import MlxLLM
from api.settings import Settings
from rag.retriever import Retriever

from .builder import split_train_valid, to_chat_example, write_jsonl
from .filter import format_ok
from .generate import generate_candidates
from .questions import load_questions

_REPO_ROOT = Path(__file__).resolve().parents[4]
_OUT_DIR = _REPO_ROOT / "data" / "ft"


def _arg(name: str, default):
    if name in sys.argv:
        return type(default)(sys.argv[sys.argv.index(name) + 1])
    return default


def main() -> None:
    k = _arg("--k", 6)
    per_q = _arg("--per-q", 2)          # 질문당 채택할 최대 후보 수(근거 점수 상위)
    min_ground = _arg("--min-ground", 0.5)

    settings = Settings.from_env()
    retriever = Retriever(settings.rag)
    llm = MlxLLM(settings.mlx_model)
    def judge_fn(prompt):
        return "".join(llm.stream(
            [{"role": "user", "content": prompt}], max_tokens=16, temperature=0.0))

    questions = load_questions()
    examples: list[dict] = []
    n_cand = n_pass = 0
    for i, q in enumerate(questions, 1):
        hits, cands = generate_candidates(q, retriever=retriever, llm=llm,
                                          judge_fn=judge_fn, k=k, temperature=0.7)
        n_cand += len(cands)
        kept = [c for c in cands if format_ok(c.answer, sources=c.sources)
                and c.grounded >= min_ground]
        kept.sort(key=lambda c: c.grounded, reverse=True)
        kept = kept[:per_q]
        n_pass += len(kept)
        for c in kept:
            examples.append(to_chat_example(q, hits, c.answer))
        print(f"[{i}/{len(questions)}] kept {len(kept)}/{len(cands)} (총 {len(examples)})")

    train, valid = split_train_valid(examples, valid_every=10)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(_OUT_DIR / "train.jsonl", train)
    write_jsonl(_OUT_DIR / "valid.jsonl", valid)
    stats = {"questions": len(questions), "candidates": n_cand, "kept": n_pass,
             "pass_rate": (n_pass / n_cand if n_cand else 0.0),
             "train": len(train), "valid": len(valid),
             "k": k, "per_q": per_q, "min_ground": min_ground}
    (_OUT_DIR / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2),
                                         encoding="utf-8")
    print("\n=== 빌드 요약 ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"저장: {_OUT_DIR}/train.jsonl, valid.jsonl, stats.json")


if __name__ == "__main__":
    main()
