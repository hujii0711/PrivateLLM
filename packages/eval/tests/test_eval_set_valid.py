from pathlib import Path

from eval.dataset import load_eval_set

EVAL_SET = Path(__file__).resolve().parents[1] / "eval_set.jsonl"


def test_eval_set_loads_and_is_nonempty():
    items = load_eval_set(EVAL_SET)
    assert len(items) >= 16


def test_every_item_has_question_and_unique_id():
    items = load_eval_set(EVAL_SET)
    ids = [it.id for it in items]
    assert len(ids) == len(set(ids))                 # id 유일
    assert all(it.question.strip() for it in items)  # 질문 비어있지 않음


def test_expected_refs_look_like_article_numbers():
    items = load_eval_set(EVAL_SET)
    for it in items:
        for ref in it.expected_refs:
            assert ref.startswith("제") and "조" in ref, (it.id, ref)
