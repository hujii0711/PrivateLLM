"""
runner.py — 평가 러너(Evaluation Runner): 평가 항목 1개를 실행하고 지표를 수집하는 모듈

【평가 러너의 역할】
평가 데이터셋의 각 항목(EvalItem)에 대해:
  1. 검색 단계 실행 → retrieval_hit 측정
  2. 챗봇 답변 생성 → run_chat() 호출
  3. 답변 형식 지표 측정 → answer_metrics()
  4. LLM-as-Judge 점수 측정 → groundedness_score()
  5. 결과를 ItemResult 에 모아 반환

【단일 책임 원칙(Single Responsibility Principle)】
runner.py 는 "한 항목의 평가 실행"만 담당합니다.
  - 전체 평가셋 순회 및 파일 저장 → cli.py
  - 결과 집계(평균 계산) → report.py
  이렇게 역할을 분리하면 각 부분을 독립적으로 테스트하고 교체할 수 있습니다.
"""

from collections.abc import Callable  # 함수 타입 힌트
from dataclasses import dataclass  # 데이터클래스 선언 도구

from api.pipeline import run_chat  # RAG 파이프라인 실행 함수

from .answer_metrics import answer_metrics  # 답변 형식·키워드 지표
from .dataset import EvalItem  # 평가 항목 데이터 타입
from .judge import groundedness_score  # LLM-as-Judge 근거성 점수
from .retrieval_metrics import ref_hit  # 검색 hit 판정


# ══════════════════════════════════════════════════════════════
# ItemResult — 평가 항목 1개의 결과 데이터
# ══════════════════════════════════════════════════════════════
@dataclass
class ItemResult:
    """평가 항목 1건의 실행 결과를 담는 데이터 클래스.

    report.aggregate() 가 이 객체 목록을 받아 전체 지표 평균을 계산합니다.

    Attributes:
        id             : 평가 항목 ID (EvalItem.id 와 동일)
        question       : 실행한 질문 텍스트
        answer         : 챗봇이 생성한 최종 답변
        retrieval_hit  : 기대 법조항이 top-k 검색 결과에 있었는지 여부
        metrics        : answer_metrics() 반환값 딕셔너리
                         (has_citation, has_structure, has_disclaimer 등)
        groundedness   : LLM-as-Judge 가 부여한 근거성 점수 (0.0 ~ 1.0)
    """

    id: str
    question: str
    answer: str
    retrieval_hit: bool
    metrics: dict
    groundedness: float


# ══════════════════════════════════════════════════════════════
# 평가 실행 함수
# ══════════════════════════════════════════════════════════════
def run_item(
    item: EvalItem,  # 실행할 평가 항목
    *,  # 이후 인자 키워드 전용
    retriever,  # 벡터 DB 검색 객체
    llm,  # 답변 생성 LLM 객체
    judge_fn: Callable[[str], str],  # 평가용 LLM 호출 함수
    top_k: int = 6,  # 검색 결과 최대 수 (현재 미사용, 인터페이스 일관성용)
) -> ItemResult:
    """평가 항목 1개에 대해 검색→생성→지표 계산을 실행합니다.

    처리 흐름:
      1. retriever.retrieve(question) : 관련 법조항 검색
      2. ref_hit()                    : 기대 법조항 검색 성공 여부 판정
      3. run_chat()                   : RAG 파이프라인으로 답변 생성
      4. answer_metrics()             : 형식·키워드 지표 계산
      5. groundedness_score()         : LLM-as-Judge 근거성 점수 계산
      6. ItemResult 로 묶어 반환

    Args:
        item      : 실행할 평가 항목 (질문, 기대 ref, 필수 키워드 포함)
        retriever : Retriever 인스턴스 (벡터 DB 검색)
        llm       : LLM 인스턴스 (답변 생성)
        judge_fn  : 프롬프트 문자열을 받아 LLM 응답 문자열을 반환하는 함수
        top_k     : 검색 결과 최대 수 (설정 일관성을 위해 전달, 직접 사용하지는 않음)

    Returns:
        ItemResult : 이 평가 항목의 모든 지표를 담은 결과 객체
    """
    # Step 1: 벡터 DB에서 관련 문서 검색
    hits = retriever.retrieve(item.question)

    # 검색된 문서들의 ref 코드 목록 추출 (ref_hit 판정에 사용)
    retrieved_refs = [h.ref for h in hits]

    # Step 2: 기대 법조항 중 하나라도 검색됐는지 확인
    hit = ref_hit(retrieved_refs=retrieved_refs, expected_refs=item.expected_refs)

    # Step 3: RAG 파이프라인 실행 → 스트리밍 이벤트를 전부 모아 리스트로 변환
    # run_chat() 는 제너레이터이므로 list() 로 감싸서 모든 이벤트를 수집합니다.
    events = list(run_chat(item.question, retriever=retriever, llm=llm))

    # "type": "done" 인 이벤트가 최종 결과 이벤트입니다.
    # next(generator) : 조건에 맞는 첫 번째 항목을 반환합니다.
    done = next(e for e in events if e["type"] == "done")
    answer, sources = done["answer"], done["sources"]

    # Step 4: 답변 형식·키워드 지표 계산
    metrics = answer_metrics(answer, sources=sources, must_mention=item.must_mention)

    # Step 5: LLM-as-Judge 근거성 점수 계산
    grounded = groundedness_score(
        question=item.question,
        answer=answer,
        contexts=[h.text for h in hits],  # 근거 문서 본문 목록
        judge_fn=judge_fn,
    )

    # Step 6: 결과 조합 후 반환
    return ItemResult(
        id=item.id,
        question=item.question,
        answer=answer,
        retrieval_hit=hit,
        metrics=metrics,
        groundedness=grounded,
    )
