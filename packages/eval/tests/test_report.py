from eval.report import aggregate
from eval.runner import ItemResult


def _r(hit, cit, disc, cov, ground):
    return ItemResult(id="x", question="q", answer="a", retrieval_hit=hit,
                      metrics={"has_citation": cit, "has_structure": True,
                               "has_disclaimer": disc, "has_sources": cit,
                               "mention_coverage": cov},
                      groundedness=ground)


def test_aggregate_means():
    results = [
        _r(True, True, True, 1.0, 0.9),
        _r(True, False, True, 0.5, 0.7),
        _r(False, True, False, 0.0, 0.5),
    ]
    agg = aggregate(results)
    assert agg["n"] == 3
    assert abs(agg["recall_at_k"] - 2 / 3) < 1e-9
    assert abs(agg["citation_rate"] - 2 / 3) < 1e-9
    assert abs(agg["disclaimer_rate"] - 2 / 3) < 1e-9
    assert abs(agg["mention_coverage"] - 0.5) < 1e-9
    assert abs(agg["groundedness"] - (0.9 + 0.7 + 0.5) / 3) < 1e-9


def test_aggregate_empty():
    agg = aggregate([])
    assert agg["n"] == 0
