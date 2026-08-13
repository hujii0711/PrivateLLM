from eval.dataset import EvalItem, load_eval_set


def test_eval_item_fields():
    it = EvalItem(id="q1", question="보증금 못 받았어요",
                  expected_refs=["제3조의2"], must_mention=["우선변제"])
    assert it.id == "q1"
    assert it.expected_refs == ["제3조의2"]


def test_load_eval_set(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text(
        '{"id":"q1","question":"보증금?","expected_refs":["제3조의2"],"must_mention":["우선변제"]}\n'
        '{"id":"q2","question":"기간?","expected_refs":["제4조"],"must_mention":[]}\n',
        encoding="utf-8",
    )
    items = load_eval_set(p)
    assert len(items) == 2
    assert items[0].id == "q1" and items[1].expected_refs == ["제4조"]


def test_load_skips_blank_lines(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('{"id":"q1","question":"x","expected_refs":[],"must_mention":[]}\n\n',
                 encoding="utf-8")
    assert len(load_eval_set(p)) == 1
