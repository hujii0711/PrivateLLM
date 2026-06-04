"""항목 결과 집계."""
from .runner import ItemResult


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def aggregate(results: list[ItemResult]) -> dict:
    if not results:
        return {"n": 0}
    return {
        "n": len(results),
        "recall_at_k": _mean([1.0 if r.retrieval_hit else 0.0 for r in results]),
        "citation_rate": _mean([1.0 if r.metrics["has_citation"] else 0.0 for r in results]),
        "structure_rate": _mean([1.0 if r.metrics["has_structure"] else 0.0 for r in results]),
        "disclaimer_rate": _mean([1.0 if r.metrics["has_disclaimer"] else 0.0 for r in results]),
        "sources_rate": _mean([1.0 if r.metrics["has_sources"] else 0.0 for r in results]),
        "mention_coverage": _mean([r.metrics["mention_coverage"] for r in results]),
        "groundedness": _mean([r.groundedness for r in results]),
    }
