"""RAG 오케스트레이션: 검색 → 근거 판정 → 프롬프트 → 스트리밍 생성 → 인용 정리."""
from typing import Iterator

from rag.citations import extract_sources, strip_invalid_citations
from rag.prompt import build_messages

NO_GROUNDING_MSG = (
    "죄송합니다. 질문과 충분히 관련된 근거(법령·판례)를 찾지 못했습니다. "
    "주택임대차 보증금 반환과 관련된 구체적 상황(예: 계약 종료 여부, 보증금 액수, "
    "임차권등기 여부 등)으로 다시 질문해 주세요.\n\n"
    "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다."
)


def run_chat(query: str, *, retriever, llm, max_tokens: int = 768,
             temperature: float = 0.3) -> Iterator[dict]:
    """이벤트 스트림을 yield한다.
    {"type":"token","text":...} (0개 이상) → {"type":"done","answer":str,"sources":[...]}
    """
    hits = retriever.retrieve(query)
    if not retriever.is_grounded(hits):
        yield {"type": "token", "text": NO_GROUNDING_MSG}
        yield {"type": "done", "answer": NO_GROUNDING_MSG, "sources": []}
        return

    messages = build_messages(query, hits)
    parts: list[str] = []
    for tok in llm.stream(messages, max_tokens=max_tokens, temperature=temperature):
        parts.append(tok)
        yield {"type": "token", "text": tok}

    raw = "".join(parts)
    answer = strip_invalid_citations(raw, hits)
    sources = [
        {"n": s.n, "title": s.title, "ref": s.ref, "url": s.url,
         "source_type": s.source_type}
        for s in extract_sources(answer, hits)
    ]
    yield {"type": "done", "answer": answer, "sources": sources}
