import json

from finetune.compare import compare_runs, load_summary, to_markdown


def test_load_summary_reads_summary_block(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"label": "x", "summary": {"recall_at_k": 0.8},
                             "items": []}), encoding="utf-8")
    assert load_summary(p) == {"recall_at_k": 0.8}


def test_compare_runs_computes_deltas():
    base = {"recall_at_k": 0.81, "structure_rate": 0.75, "citation_rate": 1.0,
            "groundedness": 0.69}
    qlora = {"recall_at_k": 0.81, "structure_rate": 0.94, "citation_rate": 1.0,
             "groundedness": 0.78}
    cmp = compare_runs(base, qlora)
    assert cmp["structure_rate"] == {"baseline": 0.75, "qlora": 0.94, "delta": 0.19}
    assert cmp["recall_at_k"]["delta"] == 0.0       # 검색 동일 → 불변
    assert cmp["citation_rate"]["delta"] == 0.0


def test_compare_only_common_metrics():
    cmp = compare_runs({"a": 1.0}, {"b": 2.0})
    assert cmp == {}


def test_to_markdown_table():
    cmp = {"structure_rate": {"baseline": 0.75, "qlora": 0.94, "delta": 0.19}}
    md = to_markdown(cmp)
    assert "structure_rate" in md
    assert "+0.19" in md or "0.19" in md
    assert "|" in md      # 표 형식
