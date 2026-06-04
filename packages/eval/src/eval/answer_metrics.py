"""답변의 형식·키워드 준수 지표(결정적)."""
import re

_CITE = re.compile(r"\[\d+\]")
_STRUCT = ("①", "②", "③")
_DISCLAIMER = "법률 자문이 아닙니다"


def answer_metrics(answer: str, *, sources: list, must_mention: list[str]) -> dict:
    has_citation = bool(_CITE.search(answer))
    has_structure = all(mark in answer for mark in _STRUCT)
    has_disclaimer = _DISCLAIMER in answer
    has_sources = len(sources) > 0
    if must_mention:
        hit = sum(1 for kw in must_mention if kw in answer)
        coverage = hit / len(must_mention)
    else:
        coverage = 1.0
    return {
        "has_citation": has_citation,
        "has_structure": has_structure,
        "has_disclaimer": has_disclaimer,
        "has_sources": has_sources,
        "mention_coverage": coverage,
    }
