"""평가 러너: 평가 항목 → 검색 + run_chat → 지표."""
from dataclasses import dataclass
from typing import Callable

from api.pipeline import run_chat

from .answer_metrics import answer_metrics
from .dataset import EvalItem
from .judge import groundedness_score
from .retrieval_metrics import ref_hit


@dataclass
class ItemResult:
    id: str
    question: str
    answer: str
    retrieval_hit: bool
    metrics: dict
    groundedness: float


def run_item(item: EvalItem, *, retriever, llm,
             judge_fn: Callable[[str], str], top_k: int = 6) -> ItemResult:
    hits = retriever.retrieve(item.question)
    retrieved_refs = [h.ref for h in hits]
    hit = ref_hit(retrieved_refs=retrieved_refs, expected_refs=item.expected_refs)

    events = list(run_chat(item.question, retriever=retriever, llm=llm))
    done = next(e for e in events if e["type"] == "done")
    answer, sources = done["answer"], done["sources"]

    metrics = answer_metrics(answer, sources=sources, must_mention=item.must_mention)
    grounded = groundedness_score(
        question=item.question, answer=answer,
        contexts=[h.text for h in hits], judge_fn=judge_fn,
    )
    return ItemResult(id=item.id, question=item.question, answer=answer,
                      retrieval_hit=hit, metrics=metrics, groundedness=grounded)
