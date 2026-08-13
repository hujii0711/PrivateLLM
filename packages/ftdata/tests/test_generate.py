from ftdata.generate import Candidate, generate_candidates
from rag.types import Retrieved


class StubRetriever:
    def retrieve(self, q):
        return [Retrieved(id="i1", text="임차인은 보증금을 우선변제 받는다", similarity=0.7,
                          source_type="법령", title="주택임대차보호법 제3조의2",
                          ref="제3조의2", url="u", date="2023")]
    def is_grounded(self, hits):
        return True


class FakeLLM:
    def __init__(self, text): self._text = text
    def stream(self, messages, **kw):
        yield self._text


def test_generate_returns_k_candidates_with_hits():
    retr = StubRetriever()
    llm = FakeLLM("① ② ③ 우선변제[1]. ※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    hits, cands = generate_candidates("보증금?", retriever=retr, llm=llm,
                                      judge_fn=lambda p: "0.8", k=3, temperature=0.7)
    assert len(hits) == 1
    assert len(cands) == 3
    c = cands[0]
    assert isinstance(c, Candidate)
    assert "우선변제" in c.answer
    assert c.sources and c.sources[0]["url"] == "u"
    assert c.grounded == 0.8
