from pathlib import Path

from ftdata.questions import load_questions

EVAL_SET = (Path(__file__).resolve().parents[3]
            / "packages" / "eval" / "eval_set.jsonl")


def _eval_questions():
    import json
    return {json.loads(line)["question"]
            for line in EVAL_SET.read_text(encoding="utf-8").splitlines() if line.strip()}


def test_pool_loads_nonempty():
    qs = load_questions()
    assert len(qs) >= 30


def test_questions_unique():
    qs = load_questions()
    assert len(qs) == len(set(qs))


def test_pool_disjoint_from_eval_set():
    # ⚠️ train/eval 오염 금지: 질문 풀과 평가셋이 하나도 겹치면 안 된다
    pool = set(load_questions())
    overlap = pool & _eval_questions()
    assert overlap == set(), overlap
