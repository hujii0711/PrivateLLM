from rag.citations import extract_sources, strip_invalid_citations
from rag.types import Retrieved


def _hits(n):
    return [Retrieved(id=f"i{i}", text=f"t{i}", similarity=0.7, source_type="법령",
                      title=f"제{i}조", ref=f"제{i}조", url=f"https://law/{i}",
                      date="2023-07-19") for i in range(1, n + 1)]


def test_extract_only_cited_sources_in_order():
    hits = _hits(3)
    answer = "보증금은 우선변제됩니다[1]. 인도와 동시이행입니다[3]."
    srcs = extract_sources(answer, hits)
    assert [s.n for s in srcs] == [1, 3]        # [2]는 인용 안 됨 → 제외
    assert srcs[0].title == "제1조" and srcs[0].url == "https://law/1"


def test_extract_dedupes_repeated_citation():
    hits = _hits(2)
    answer = "A[1]. B[1]. C[2]."
    assert [s.n for s in extract_sources(answer, hits)] == [1, 2]


def test_strip_invalid_citations_removes_out_of_range():
    hits = _hits(2)
    # [5]는 근거 범위 밖(환각) → 제거
    answer = "사실이다[1]. 또한[5]."
    assert strip_invalid_citations(answer, hits) == "사실이다[1]. 또한."


def test_extract_ignores_out_of_range():
    hits = _hits(2)
    answer = "맞다[1][9]."
    assert [s.n for s in extract_sources(answer, hits)] == [1]
