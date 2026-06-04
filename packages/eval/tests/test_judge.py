from eval.judge import groundedness_score, JUDGE_PROMPT_HINT


def test_uses_injected_judge_and_parses_score():
    # 가짜 judge: 항상 "0.8"을 반환
    score = groundedness_score(
        question="보증금?", answer="우선변제 받습니다[1].",
        contexts=["임차인은 보증금을 우선변제 받는다"],
        judge_fn=lambda prompt: "이 답변은 근거에 부합합니다. 점수: 0.8",
    )
    assert score == 0.8


def test_clamps_and_parses_first_number():
    score = groundedness_score(
        question="q", answer="a", contexts=["c"],
        judge_fn=lambda prompt: "1.0",
    )
    assert score == 1.0


def test_returns_zero_when_no_number():
    score = groundedness_score(
        question="q", answer="a", contexts=["c"],
        judge_fn=lambda prompt: "판단 불가",
    )
    assert score == 0.0


def test_judge_prompt_hint_mentions_grounding():
    assert "근거" in JUDGE_PROMPT_HINT
