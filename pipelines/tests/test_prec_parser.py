from pipelines.ingest.prec_parser import parse_prec


def test_parses_case_metadata_and_sections(fixtures_dir):
    xml = (fixtures_dir / "prec_one.xml").read_text(encoding="utf-8")
    prec = parse_prec(xml)

    assert prec["case_name"]                # 사건명
    assert prec["case_no"]                  # 사건번호
    assert prec["court"]                    # 법원명
    # 판시사항/판결요지 중 최소 하나는 비어있지 않아야 한다
    assert (prec["holding_summary"].strip() or prec["judgment_summary"].strip())


def test_sections_are_strings(fixtures_dir):
    xml = (fixtures_dir / "prec_one.xml").read_text(encoding="utf-8")
    prec = parse_prec(xml)
    for key in ("holding_summary", "judgment_summary", "body"):
        assert isinstance(prec[key], str)


def test_sections_have_no_html_br(fixtures_dir):
    xml = (fixtures_dir / "prec_one.xml").read_text(encoding="utf-8")
    prec = parse_prec(xml)
    for key in ("holding_summary", "judgment_summary", "body"):
        assert "<br" not in prec[key].lower(), prec[key][:160]


def test_br_becomes_newline_not_concatenation(fixtures_dir):
    xml = (fixtures_dir / "prec_one.xml").read_text(encoding="utf-8")
    prec = parse_prec(xml)
    # <br/> 자리에 줄바꿈이 들어가 단어가 붙어버리지 않아야 한다
    # 판시사항은 보통 여러 항목([1],[2]...)이 줄로 분리된다
    assert "\n" in prec["holding_summary"]
