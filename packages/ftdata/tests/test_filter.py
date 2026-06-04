from ftdata.filter import format_ok


def test_accepts_well_formed_answer():
    answer = ("① 상황 요약: ...\n② 적용 법리: 우선변제 받습니다[1].\n③ 다음 절차: ...\n\n"
              "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    assert format_ok(answer, sources=[{"n": 1}]) is True


def test_rejects_missing_citation():
    answer = ("① ② ③ 구조는 있지만 인용이 없습니다.\n"
              "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    assert format_ok(answer, sources=[]) is False


def test_rejects_missing_structure():
    answer = "우선변제 받습니다[1]. ※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다."
    assert format_ok(answer, sources=[{"n": 1}]) is False


def test_rejects_no_sources():
    answer = ("① ② ③ 우선변제[1].\n※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    assert format_ok(answer, sources=[]) is False
