"""질문 → 검색 근거 + run_chat로 K개 후보 답변 생성(temp 다양성) + 근거 점수."""
from collections.abc import Callable
from dataclasses import dataclass

from api.pipeline import run_chat
from eval.judge import groundedness_score
from rag.types import Retrieved


@dataclass
class Candidate:
    answer: str
    sources: list
    grounded: float


def generate_candidates(question: str, *, retriever, llm,
                        judge_fn: Callable[[str], str], k: int = 6,
                        temperature: float = 0.7) -> tuple[list[Retrieved], list[Candidate]]:
    hits = retriever.retrieve(question)
    contexts = [h.text for h in hits]
    cands: list[Candidate] = []
    for _ in range(k):
        events = list(run_chat(question, retriever=retriever, llm=llm,
                               temperature=temperature))
        done = next(e for e in events if e["type"] == "done")
        grounded = groundedness_score(question=question, answer=done["answer"],
                                      contexts=contexts, judge_fn=judge_fn)
        cands.append(Candidate(answer=done["answer"], sources=done["sources"],
                               grounded=grounded))
    return hits, cands
