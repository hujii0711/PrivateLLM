from pipelines.schema import SOURCE_TYPES, Chunk, make_chunk


def test_make_chunk_fills_all_fields():
    c: Chunk = make_chunk(
        id="law-주택임대차보호법-3조의2",
        text="임차인은 ...",
        source_type="법령",
        title="주택임대차보호법 제3조의2",
        ref="제3조의2",
        url="https://www.law.go.kr/...",
        date="2023-07-19",
    )
    assert c["id"] == "law-주택임대차보호법-3조의2"
    assert c["source_type"] == "법령"
    assert set(c.keys()) == {"id", "text", "source_type", "title", "ref", "url", "date"}


def test_make_chunk_rejects_unknown_source_type():
    import pytest

    with pytest.raises(ValueError):
        make_chunk(id="x", text="t", source_type="기타",
                   title="t", ref="r", url="u", date="2023-01-01")


def test_source_types_constant():
    assert SOURCE_TYPES == ("법령", "판례", "해설", "상담사례")
