"""
pipeline.py — RAG 오케스트레이션(Orchestration) 모듈

【이 파일이 하는 일】
사용자 질문 하나를 받아 아래 순서로 처리한 뒤, 이벤트 스트림으로 결과를 반환합니다.

  ┌──────────────┐
  │ 사용자 질문     │
  └──────┬───────┘
         │ 1. 관련 문서 검색 (Retrieval)
         ▼
  ┌──────────────┐
  │ 벡터 DB 검색 │  hits = retriever.retrieve(query)
  └──────┬───────┘
         │ 2. 근거 품질 판정 (Grounding Check)
         ▼
  ┌────────────────┐
  │ 근거 충분?       │──NO──▶ "관련 근거를 찾지 못했습니다" 메시지 반환
  └──────┬─────────┘
         │ YES
         │ 3. 프롬프트 구성 (Prompt Building)
         ▼
  ┌──────────────────┐
  │ build_messages() │  시스템 프롬프트 + 검색 결과 + 사용자 질문 조합
  └──────┬───────────┘
         │ 4. LLM 스트리밍 생성
         ▼
  ┌──────────────┐
  │ llm.stream() │  토큰 단위로 yield → 클라이언트에 즉시 전달
  └──────┬───────┘
         │ 5. 사후 처리 (Post-processing)
         ▼
  ┌──────────────────────────┐
  │ 인용 정리 + 면책 문구 추가     │
  └──────────────────────────┘

【SSE (Server-Sent Events) 이벤트 형식】
  {"type": "token", "text": "생성된 텍스트 조각"}  ← 여러 번 전송
  {"type": "done",  "answer": "전체 답변", "sources": [...]}  ← 마지막에 1번 전송
"""

from collections.abc import Iterator  # 이터레이터 타입 힌트

from rag.citations import extract_sources, strip_invalid_citations

# extract_sources       : 답변 본문에서 실제로 인용된 출처만 추출합니다.
# strip_invalid_citations: 답변에서 검색 결과에 없는 잘못된 인용 번호를 제거합니다.
from rag.prompt import build_messages

# build_messages : 검색된 문서와 사용자 질문을 LLM에 전달할 메시지 형식으로 조립합니다.


# ──────────────────────────────────────────────────────────
# 상수(Constant) 정의
# ──────────────────────────────────────────────────────────

# 모든 답변 마지막에 항상 붙는 법적 면책 문구
DISCLAIMER = "※ 본 답변은 일반적 정보 제공이며 법률 자문이 아닙니다."

# 관련 근거를 찾지 못했을 때 보여주는 안내 메시지
# 줄이 길어서 괄호로 묶어 여러 줄에 나눠 씁니다 (파이썬 문자열 암묵적 연결).
NO_GROUNDING_MSG = (
    "죄송합니다. 질문과 충분히 관련된 근거(법령·판례)를 찾지 못했습니다. "
    "주택임대차 보증금 반환과 관련된 구체적 상황(예: 계약 종료 여부, 보증금 액수, "
    "임차권등기 여부 등)으로 다시 질문해 주세요.\n\n" + DISCLAIMER
)


# ══════════════════════════════════════════════════════════════
# 헬퍼 함수 (Helper Function)
# 이름 앞에 _ 를 붙여 "이 모듈 내부용 함수"임을 나타냅니다.
# ══════════════════════════════════════════════════════════════
def _ensure_disclaimer(answer: str) -> str:
    """답변에 법적 면책 문구가 없으면 자동으로 추가합니다.

    LLM이 이미 면책 문구를 생성했다면 중복 추가를 방지합니다.

    Args:
        answer: LLM이 생성한 원본 답변 텍스트

    Returns:
        면책 문구가 포함된 최종 답변 텍스트
    """
    # "법률 자문이 아닙니다" 문구가 이미 있으면 그대로 반환
    if "법률 자문이 아닙니다" in answer:
        return answer
    # 없으면 뒤에 공백 제거 후 줄바꿈 2번 + 면책 문구 추가
    return answer.rstrip() + "\n\n" + DISCLAIMER


# ══════════════════════════════════════════════════════════════
# 메인 파이프라인 함수
# ══════════════════════════════════════════════════════════════
def run_chat(
    query: str,  # 사용자가 입력한 질문 텍스트
    *,  # 이후 인자는 반드시 키워드 인자로 전달해야 합니다
    retriever,  # 벡터 DB에서 관련 문서를 검색하는 객체 (Retriever 인스턴스)
    llm,  # 텍스트를 생성하는 LLM 객체 (MlxLLM 또는 FakeLLM)
    max_tokens: int = 768,
    temperature: float = 0.3,
) -> Iterator[dict]:
    """사용자 질문을 RAG 파이프라인으로 처리하고 이벤트를 스트리밍합니다.

    제너레이터(Generator) 함수입니다.
    return 대신 yield 를 사용해, 호출자가 for 루프로 이벤트를 하나씩 받을 수 있습니다.

    이벤트 흐름:
        1. {"type": "token", "text": "단어조각"}  ← LLM 생성 중 반복 전송
        2. {"type": "done",  "answer": "전체답변", "sources": [...]}  ← 완료 시 1회 전송

    Args:
        query      : 사용자가 입력한 질문
        retriever  : 벡터 DB 검색 객체
        llm        : 텍스트 생성 LLM 객체
        max_tokens : 최대 생성 토큰 수
        temperature: 생성 무작위성

    Yields:
        dict: 위에 설명한 형식의 이벤트 딕셔너리
    """

    # ── Step 1: 벡터 DB에서 관련 문서 검색 ───────────────────
    # retriever.retrieve(query) 는 질문과 의미적으로 유사한 법령·판례 문서를
    # 벡터 유사도 검색으로 찾아 반환합니다.
    hits = retriever.retrieve(query)
    # pprint.pprint(hits, indent=4)
    # ── Step 2: 근거 품질 판정 ───────────────────────────────
    # is_grounded(hits) 는 검색된 문서들이 질문에 답하기에 충분한지 검사합니다.
    # 관련성이 낮은 문서만 반환됐다면 False 를 반환합니다.
    if not retriever.is_grounded(hits):
        # 근거 부족: 안내 메시지를 token + done 두 이벤트로 전송하고 종료합니다.
        yield {"type": "token", "text": NO_GROUNDING_MSG}
        yield {"type": "done", "answer": NO_GROUNDING_MSG, "sources": []}
        return  # 제너레이터를 즉시 종료 (이후 코드 실행 안 함)

    # ── Step 3: 프롬프트(메시지 목록) 구성 ──────────────────
    # build_messages : 시스템 지시문 + 검색 결과(법령 본문 등) + 사용자 질문을
    # OpenAI 호환 메시지 형식([{"role": ..., "content": ...}, ...])으로 조립합니다.
    messages = build_messages(query, hits)
    # pprint.pprint(messages, indent=4)

    # ── Step 4: LLM 스트리밍 생성 ───────────────────────────
    parts: list[str] = []  # 생성된 토큰 조각들을 나중에 합치기 위해 저장

    for tok in llm.stream(messages, max_tokens=max_tokens, temperature=temperature):
        parts.append(tok)  # 토큰 조각을 누적 저장
        # 토큰이 생성될 때마다 즉시 클라이언트에 전달합니다.
        # 이 덕분에 사용자는 전체 답변 완성을 기다리지 않고 글자가 나타나는 것을 볼 수 있습니다.
        yield {"type": "token", "text": tok}

    # ── Step 5: 사후 처리 ────────────────────────────────────
    # 모든 토큰 조각을 하나의 문자열로 합칩니다.
    raw = "".join(parts)

    # strip_invalid_citations : LLM이 환각(Hallucination)으로 만들어낸
    # 잘못된 인용 번호를 제거합니다. (예: [99] 처럼 실제로 없는 번호)
    # _ensure_disclaimer       : 면책 문구가 없으면 추가합니다.
    answer = _ensure_disclaimer(strip_invalid_citations(raw, hits))
    # print(f"[run_chat] answer:\n{answer}")
    # extract_sources : 최종 답변에서 실제로 참조된 출처 목록만 추출합니다.
    # 딕셔너리 컴프리헨션으로 SourceOut 스키마에 맞게 변환합니다.
    sources = [
        {
            "n": s.n,  # 인용 번호
            "title": s.title,  # 출처 제목
            "ref": s.ref,  # 본문 내 참조 표기 (예: "[1]")
            "url": s.url,  # 원문 URL
            "source_type": s.source_type,  # 출처 유형 (law, case 등)
        }
        for s in extract_sources(answer, hits)
    ]

    # 최종 완료 이벤트: 전체 답변과 인용 출처 목록을 한꺼번에 전송합니다.
    yield {"type": "done", "answer": answer, "sources": sources}
