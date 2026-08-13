from api.llm import FakeLLM
from api.pipeline import run_chat
from rag.types import Retrieved


class StubRetriever:
    def __init__(self, hits, grounded=True):
        self._hits = hits
        self._grounded = grounded
    def retrieve(self, query):
        return self._hits
    def is_grounded(self, hits):
        return self._grounded


def _hit(n):
    return Retrieved(id=f"i{n}", text=f"근거{n}", similarity=0.7, source_type="법령",
                     title=f"주택임대차보호법 제{n}조", ref=f"제{n}조",
                     url=f"https://law/{n}", date="2023-07-19")


def test_run_chat_streams_answer_then_sources():
    retr = StubRetriever([_hit(1), _hit(2)])
    llm = FakeLLM(["보증금은 ", "우선변제[1] ", "됩니다."])
    events = list(run_chat("보증금?", retriever=retr, llm=llm))

    tokens = [e for e in events if e["type"] == "token"]
    final = [e for e in events if e["type"] == "done"][0]
    assert "".join(t["text"] for t in tokens) == "보증금은 우선변제[1] 됩니다."
    # 실제 인용된 [1]만 sources에 (그리고 [2]는 인용 안 됨)
    assert [s["n"] for s in final["sources"]] == [1]
    assert final["sources"][0]["url"] == "https://law/1"


def test_run_chat_strips_hallucinated_citation_from_final():
    retr = StubRetriever([_hit(1)])
    llm = FakeLLM(["사실[1] ", "환각[7]"])   # [7]은 근거 범위 밖
    events = list(run_chat("q", retriever=retr, llm=llm))
    final = [e for e in events if e["type"] == "done"][0]
    assert "[7]" not in final["answer"]
    assert [s["n"] for s in final["sources"]] == [1]


def test_run_chat_appends_disclaimer_when_model_omits_it():
    from api.pipeline import DISCLAIMER, run_chat
    retr = StubRetriever([_hit(1)])
    llm = FakeLLM(["보증금은 우선변제됩니다[1]."])   # 모델이 면책 고지를 빠뜨림
    final = [e for e in run_chat("q", retriever=retr, llm=llm) if e["type"] == "done"][0]
    assert final["answer"].endswith(DISCLAIMER)
    assert final["answer"].count("법률 자문이 아닙니다") == 1


def test_run_chat_does_not_double_append_disclaimer():
    from api.pipeline import run_chat
    retr = StubRetriever([_hit(1)])
    llm = FakeLLM(["답변[1].\n\n※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다."])
    final = [e for e in run_chat("q", retriever=retr, llm=llm) if e["type"] == "done"][0]
    assert final["answer"].count("법률 자문이 아닙니다") == 1   # 중복 없음


def test_run_chat_no_grounding_returns_fallback_without_calling_llm():
    called = {"n": 0}
    class LoudLLM:
        def stream(self, *a, **k):
            called["n"] += 1
            yield "should not happen"
    retr = StubRetriever([], grounded=False)
    events = list(run_chat("관련 없는 질문", retriever=retr, llm=LoudLLM()))
    final = [e for e in events if e["type"] == "done"][0]
    assert called["n"] == 0                       # 근거 없으면 LLM 호출 안 함
    assert "근거" in final["answer"]               # 안내 메시지
    assert final["sources"] == []
