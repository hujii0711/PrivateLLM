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


def test_article_text_excludes_metadata_noise(fixtures_dir):
    xml = (fixtures_dir / "law_주택임대차보호법.xml").read_text(encoding="utf-8")
    law = parse_law(xml)
    by_no = {a["article_no"]: a for a in law["articles"]}

    art1 = by_no["제1조"]
    # 본문은 실제 조문내용으로 시작해야 한다
    assert art1["text"].startswith("제1조"), art1["text"][:80]
    # 조문시행일자 같은 메타데이터가 본문에 섞이면 안 된다
    assert "20260102" not in art1["text"]
    # 조문여부 리터럴 '조문'이 줄 단독으로 들어가면 안 된다
    assert "\n조문\n" not in ("\n" + art1["text"] + "\n")

    # 다항 조문도 본문 텍스트가 실제 내용으로 시작
    art3 = by_no["제3조"]
    assert art3["text"].startswith("제3조"), art3["text"][:80]
    assert "20260102" not in art3["text"]
    # 항번호 마커가 항내용 앞에 중복으로 남지 않아야 한다 (예: '①\n① ...' 금지)
    import re
    assert not re.search(r"(^|\n)([①-⑮])\n\2", art3["text"]), art3["text"][:200]
