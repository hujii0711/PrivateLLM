from eval.dataset import EvalItem
from eval.runner import run_item, ItemResult
from rag.types import Retrieved


class StubRetriever:
    def __init__(self, refs):
        self._refs = refs
    def retrieve(self, q):
        return [Retrieved(id=f"i{i}", text=f"근거{r}", similarity=0.7, source_type="법령",
                          title=f"주택임대차보호법 {r}", ref=r, url=f"u{i}", date="2023")
                for i, r in enumerate(self._refs)]
    def is_grounded(self, hits):
        return True


class FakeLLM:
    def __init__(self, text): self._text = text
    def stream(self, messages, **kw):
        yield self._text


def test_run_item_computes_retrieval_and_answer_metrics():
    item = EvalItem(id="q1", question="보증금?", expected_refs=["제3조의2"],
                    must_mention=["우선변제"])
    retr = StubRetriever(["제3조의2", "제4조"])
    llm = FakeLLM("① ② ③ 우선변제 받습니다[1]. ※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다.")
    res = run_item(item, retriever=retr, llm=llm, judge_fn=lambda p: "0.9", top_k=6)

    assert isinstance(res, ItemResult)
    assert res.retrieval_hit is True              # 제3조의2 검색됨
    assert res.metrics["has_citation"] is True
    assert res.metrics["has_disclaimer"] is True
    assert res.metrics["mention_coverage"] == 1.0
    assert res.groundedness == 0.9


def test_run_item_retrieval_miss():
    item = EvalItem(id="q2", question="기간?", expected_refs=["제4조"], must_mention=[])
    retr = StubRetriever(["제3조의2"])             # 제4조 없음
    llm = FakeLLM("답변[1].")
    res = run_item(item, retriever=retr, llm=llm, judge_fn=lambda p: "0.5", top_k=6)
    assert res.retrieval_hit is False
