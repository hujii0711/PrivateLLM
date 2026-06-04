"""학습 후보 형식 필터 — 평가의 answer_metrics를 재사용해 품질 기준을 일치시킨다."""
from eval.answer_metrics import answer_metrics


def format_ok(answer: str, *, sources: list) -> bool:
    """상담형 구조·[n] 인용·면책·출처를 모두 갖춘 후보만 통과."""
    m = answer_metrics(answer, sources=sources, must_mention=[])
    return (m["has_citation"] and m["has_structure"]
            and m["has_disclaimer"] and m["has_sources"])
