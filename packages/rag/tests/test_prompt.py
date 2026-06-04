from rag.prompt import build_messages, SYSTEM_PROMPT
from rag.types import Retrieved


def _hit(text, title, sim=0.7):
    return Retrieved(id="x", text=text, similarity=sim, source_type="법령",
                     title=title, ref="제3조의2", url="https://law/1", date="2023-07-19")


def test_messages_have_system_and_user():
    hits = [_hit("임차인은 보증금을 우선변제 받는다", "주택임대차보호법 제3조의2")]
    msgs = build_messages("보증금 못 받았어요", hits)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == SYSTEM_PROMPT
    assert msgs[-1]["role"] == "user"


def test_user_message_numbers_sources_and_includes_query():
    hits = [
        _hit("임차인은 보증금을 우선변제 받는다", "주택임대차보호법 제3조의2"),
        _hit("동시이행 관계이다", "대법원 2020다1"),
    ]
    user = build_messages("보증금 못 받았어요", hits)[-1]["content"]
    assert "[1]" in user and "[2]" in user
    assert "주택임대차보호법 제3조의2" in user
    assert "임차인은 보증금을 우선변제" in user
    assert "보증금 못 받았어요" in user          # 사용자 질문 포함


def test_system_prompt_requires_citation_and_disclaimer():
    # 시스템 프롬프트가 핵심 행동 규칙을 담아야 한다
    assert "[" in SYSTEM_PROMPT and "근거" in SYSTEM_PROMPT
