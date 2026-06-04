"""답변의 [n] 인용을 검증해 실제 근거(Source)로 매핑하고, 환각 인용을 제거한다."""
import re

from .types import Retrieved, Source

_CITE = re.compile(r"\[(\d+)\]")


def extract_sources(answer: str, hits: list[Retrieved]) -> list[Source]:
    """답변에 등장한 유효 인용 번호를 등장 순서대로(중복 제거) Source 리스트로 반환."""
    seen: set[int] = set()
    sources: list[Source] = []
    for m in _CITE.finditer(answer):
        n = int(m.group(1))
        if 1 <= n <= len(hits) and n not in seen:
            seen.add(n)
            h = hits[n - 1]
            sources.append(Source(n=n, title=h.title, ref=h.ref, url=h.url,
                                   source_type=h.source_type))
    return sources


def strip_invalid_citations(answer: str, hits: list[Retrieved]) -> str:
    """근거 범위를 벗어난 [n] 인용(환각)을 답변 텍스트에서 제거."""
    def repl(m):
        n = int(m.group(1))
        return m.group(0) if 1 <= n <= len(hits) else ""
    return _CITE.sub(repl, answer)
