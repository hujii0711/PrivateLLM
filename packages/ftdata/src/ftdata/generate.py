"""질문 → 검색 근거 + run_chat로 K개 후보 답변 생성(temp 다양성) + 근거 점수.

이 모듈은 파인튜닝 데이터를 만들기 위해,
하나의 질문에 대해 여러 개의 "후보 답변"을 생성하고
각 답변이 얼마나 근거(문서)에 기반했는지 점수를 매깁니다.

흐름 요약:
  1. 질문을 받아 관련 문서(hits)를 검색한다.
  2. temperature(다양성 조절 파라미터)를 이용해 k번 답변을 생성한다.
  3. 각 답변에 대해 근거 점수(grounded)를 계산한다.
  4. 후보(Candidate) 목록을 반환한다.
"""

from collections.abc import Callable  # 함수(콜백)를 타입 힌트로 쓰기 위한 임포트
from dataclasses import dataclass  # 데이터 클래스를 간편하게 만들기 위한 데코레이터

from api.pipeline import run_chat  # 실제로 LLM에게 답변을 생성시키는 함수
from eval.judge import groundedness_score  # 답변이 근거 문서에 얼마나 충실한지 점수화
from rag.types import Retrieved  # 검색 결과 한 건을 나타내는 타입


@dataclass
class Candidate:
    """후보 답변 하나를 담는 데이터 클래스.

    Attributes:
        answer:   LLM이 생성한 답변 텍스트.
        sources:  답변에 사용된 출처(문서) 목록.
        grounded: 근거 점수 (0.0 ~ 1.0). 높을수록 출처에 충실한 답변.
    """

    answer: str  # 생성된 답변 텍스트
    sources: list  # 답변에 인용된 출처 목록
    grounded: float  # 근거 충실도 점수 (0~1)


def generate_candidates(
    question: str,
    *,
    retriever,  # 문서 검색기 객체 (RAG의 핵심)
    llm,  # 언어 모델 객체
    judge_fn: Callable[[str], str],  # 근거 평가에 사용할 LLM 호출 함수
    k: int = 6,  # 생성할 후보 답변 수 (기본값 6개)
    temperature: float = 0.7,  # 답변 다양성 조절 (0에 가까울수록 일관됨, 높을수록 다양함)
) -> tuple[list[Retrieved], list[Candidate]]:
    """하나의 질문에 대해 k개의 후보 답변을 생성하고 근거 점수를 붙여 반환합니다.

    Args:
        question:    사용자 질문 문자열.
        retriever:   관련 문서를 검색하는 객체.
        llm:         텍스트를 생성하는 언어 모델 객체.
        judge_fn:    근거 점수 판정에 쓸 LLM 호출 함수.
        k:           생성할 후보 답변의 개수.
        temperature: 답변 다양성 파라미터 (0=결정적, 1=무작위에 가까움).

    Returns:
        (hits, cands) 튜플:
          - hits:  검색된 문서(Retrieved) 목록 — 모든 후보가 공유.
          - cands: Candidate 객체 목록 (답변 + 출처 + 근거 점수).
    """
    # 1단계: 질문과 관련된 문서를 검색합니다.
    hits = retriever.retrieve(question)

    # 검색된 문서들에서 텍스트만 추출합니다.
    # 이 텍스트들이 답변 생성의 "근거(context)"가 됩니다.
    contexts = [h.text for h in hits]

    cands: list[Candidate] = []  # 후보 답변을 담을 빈 리스트

    # 2단계: k번 반복하여 다양한 답변 후보를 생성합니다.
    # temperature가 0.7이면 매번 조금씩 다른 답변이 나옵니다.
    for _ in range(k):
        # run_chat은 이벤트(event)를 순서대로 내보내는 제너레이터입니다.
        # list()로 감싸서 모든 이벤트를 한꺼번에 받아옵니다.
        events = list(run_chat(question, retriever=retriever, llm=llm, temperature=temperature))

        # 이벤트 목록에서 type이 "done"인 이벤트를 찾습니다.
        # "done" 이벤트에 최종 답변(answer)과 출처(sources)가 담겨 있습니다.
        done = next(e for e in events if e["type"] == "done")

        # 3단계: 이 답변이 검색된 문서를 얼마나 잘 반영했는지 점수를 계산합니다.
        grounded = groundedness_score(
            question=question,
            answer=done["answer"],
            contexts=contexts,
            judge_fn=judge_fn,
        )

        # Candidate 객체로 묶어 리스트에 추가합니다.
        cands.append(
            Candidate(
                answer=done["answer"],
                sources=done["sources"],
                grounded=grounded,
            )
        )

    return hits, cands
