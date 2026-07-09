"""
retrieval_metrics.py — 검색(Retrieval) 단계 품질 지표 계산 모듈

【검색 평가란?】
RAG 시스템에서 LLM 답변 품질 못지않게 중요한 것이 검색 단계입니다.
올바른 법조항이 검색되지 않으면, 아무리 좋은 LLM 도 올바른 답변을 할 수 없습니다.
이 모듈은 "기대한 법조항이 실제로 검색됐는가"를 측정합니다.

【Recall@K (재현율@K) 란?】
정보 검색(Information Retrieval) 분야의 핵심 지표입니다.

  Recall@K = (K개 결과에서 찾은 정답 수) / (전체 정답 수)

이 프로젝트에서는 평가 항목별로 "기대 ref 중 하나라도 top-k 에 있으면 hit=1" 로 단순화합니다.
  recall_at_k = (hit=1 인 항목 수) / (전체 항목 수)

【평가 흐름】
  평가 항목별 ref_hit() 결과 → [True, True, False, True, ...]
                               → recall_at_k() → 평균 hit 율 (예: 0.75)
"""


def ref_hit(*, retrieved_refs: list[str], expected_refs: list[str]) -> bool:
    """기대 법조항 ref 중 하나라도 검색 결과에 있으면 True 를 반환합니다.

    "Hit" = 검색 성공 (기대한 문서를 찾음)
    "Miss" = 검색 실패 (기대한 문서를 못 찾음)

    특수 케이스:
        expected_refs 가 비어 있으면 → 평가 기준이 없으므로 항상 True 반환
        (이 항목은 검색 품질 평가에서 제외됩니다)

    Args:
        retrieved_refs : 실제로 검색된 문서들의 ref 코드 목록
                         (Retrieved 객체의 ref 필드 값들)
                         예: ["제3조의3", "제6조", "제8조"]
        expected_refs  : 이 질문에서 찾아야 할 정답 ref 코드 목록
                         (EvalItem 의 expected_refs 필드)
                         예: ["제3조의3"]

    Returns:
        True  : 평가 대상 없음(기대 ref 없음) 또는 기대 ref 중 하나가 검색됨
        False : 기대 ref 가 있지만 검색 결과에 하나도 없음
    """
    # 기대 ref 가 없으면 검색 품질 평가 불가 → 평가 제외 (True 반환)
    if not expected_refs:
        return True

    # set 변환: 리스트보다 집합(set) 에서 `in` 검사가 O(1) 로 빠릅니다.
    retrieved = set(retrieved_refs)

    # any() : 이터러블에서 하나라도 True 이면 True 반환
    # 기대 ref 중 하나라도 검색된 ref 집합에 있으면 hit 성공
    return any(r in retrieved for r in expected_refs)


def recall_at_k(per_item_hits: list[bool]) -> float:
    """항목별 hit 결과 리스트를 평균 hit 율(Recall@K)로 집계합니다.

    Args:
        per_item_hits : 각 평가 항목의 ref_hit() 결과 불리언 리스트
                        예: [True, True, False, True] → Recall@K = 3/4 = 0.75

    Returns:
        0.0 ~ 1.0 사이의 평균 hit 율
        리스트가 비어있으면 0.0 반환 (ZeroDivisionError 방지)
    """
    if not per_item_hits:
        return 0.0

    # h 가 True 인 항목 수를 전체 항목 수로 나눕니다.
    # sum(1 for h in ... if h) : True 인 항목의 개수를 셉니다.
    return sum(1 for h in per_item_hits if h) / len(per_item_hits)
