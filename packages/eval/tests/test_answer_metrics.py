from eval.answer_metrics import answer_metrics


def test_detects_citation_structure_disclaimer():
    answer = ("① 상황 요약: ...\n② 적용 법리: 우선변제 받습니다[1].\n③ 다음 절차: ...\n\n"
              "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    m = answer_metrics(answer, sources=[{"n": 1}], must_mention=["우선변제"])
    assert m["has_citation"] is True
    assert m["has_structure"] is True
    assert m["has_disclaimer"] is True
    assert m["has_sources"] is True
    assert m["mention_coverage"] == 1.0


def test_missing_signals():
    m = answer_metrics("그냥 평범한 답변입니다.", sources=[], must_mention=["우선변제", "확정일자"])
    assert m["has_citation"] is False
    assert m["has_structure"] is False
    assert m["has_disclaimer"] is False
    assert m["has_sources"] is False
    assert m["mention_coverage"] == 0.0


def test_partial_mention_coverage():
    m = answer_metrics("확정일자가 중요합니다[1].", sources=[{"n": 1}],
                       must_mention=["우선변제", "확정일자"])
    assert m["mention_coverage"] == 0.5    # 2개 중 1개 포함


def test_mention_coverage_is_one_when_no_keywords():
    m = answer_metrics("아무 답변[1].", sources=[{"n": 1}], must_mention=[])
    assert m["mention_coverage"] == 1.0
