from pipelines.chunk.chunker import chunk_law, chunk_prec


def test_chunk_law_one_chunk_per_article():
    law = {
        "law_name": "주택임대차보호법",
        "source_url": "https://www.law.go.kr/법령/주택임대차보호법",
        "articles": [
            {"article_no": "제3조의2", "title": "보증금의 회수", "text": "임차인은 ..."},
            {"article_no": "제4조", "title": "임대차기간", "text": "기간을 정하지 ..."},
        ],
    }
    chunks = chunk_law(law, date="2023-07-19")
    assert len(chunks) == 2
    c = chunks[0]
    assert c["source_type"] == "법령"
    assert c["title"] == "주택임대차보호법 제3조의2(보증금의 회수)"
    assert c["ref"] == "제3조의2"
    assert "임차인은" in c["text"]
    assert c["id"] == "law-주택임대차보호법-제3조의2"


def test_chunk_prec_splits_sections():
    prec = {
        "prec_id": "98765",
        "case_name": "보증금반환",
        "case_no": "2020다12345",
        "court": "대법원",
        "decided_on": "20210115",
        "holding_summary": "임대차 종료 후 ...",
        "judgment_summary": "동시이행 관계에 ...",
        "body": "...",
        "source_url": "https://www.law.go.kr/판례/98765",
    }
    chunks = chunk_prec(prec)
    refs = {c["ref"] for c in chunks}
    assert refs == {"판시사항", "판결요지"}
    for c in chunks:
        assert c["source_type"] == "판례"
        assert c["title"].startswith("대법원 2020다12345")
        assert c["date"] == "2021-01-15"


def test_chunk_prec_skips_empty_sections():
    prec = {
        "prec_id": "1", "case_name": "x", "case_no": "2020다1", "court": "대법원",
        "decided_on": "20210115", "holding_summary": "", "judgment_summary": "내용",
        "body": "", "source_url": "u",
    }
    chunks = chunk_prec(prec)
    assert len(chunks) == 1 and chunks[0]["ref"] == "판결요지"
