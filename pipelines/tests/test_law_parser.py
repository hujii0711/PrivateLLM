from pipelines.ingest.law_parser import parse_law


def test_parses_law_name_and_articles(fixtures_dir):
    xml = (fixtures_dir / "law_주택임대차보호법.xml").read_text(encoding="utf-8")
    law = parse_law(xml)

    assert law["law_name"] == "주택임대차보호법"
    assert law["articles"], "조문이 하나 이상 추출돼야 한다"

    art = law["articles"][0]
    assert set(art.keys()) == {"article_no", "title", "text"}
    assert art["article_no"]            # 예: "제1조"
    assert isinstance(art["text"], str) and art["text"].strip()


def test_every_article_has_nonempty_text(fixtures_dir):
    xml = (fixtures_dir / "law_주택임대차보호법.xml").read_text(encoding="utf-8")
    law = parse_law(xml)
    assert all(a["text"].strip() for a in law["articles"])
