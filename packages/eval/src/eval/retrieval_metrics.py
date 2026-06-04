"""검색 품질 지표: 기대 법조항이 top-k에 검색됐는가."""


def ref_hit(*, retrieved_refs: list[str], expected_refs: list[str]) -> bool:
    """기대 ref가 하나도 없으면 평가 제외(True). 있으면 그 중 하나라도 검색되면 True."""
    if not expected_refs:
        return True
    retrieved = set(retrieved_refs)
    return any(r in retrieved for r in expected_refs)


def recall_at_k(per_item_hits: list[bool]) -> float:
    """항목별 hit 불리언 리스트 → 평균 hit율."""
    if not per_item_hits:
        return 0.0
    return sum(1 for h in per_item_hits if h) / len(per_item_hits)
