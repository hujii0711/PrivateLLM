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
