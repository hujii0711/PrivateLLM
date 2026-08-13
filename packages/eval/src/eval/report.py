"""
report.py — 평가 결과 집계(Aggregation) 모듈

【집계(Aggregation) 란?】
개별 평가 항목의 결과(ItemResult) 여러 개를 받아
전체 시스템의 성능을 나타내는 요약 지표를 계산합니다.

예시:
  항목 1: recall_hit=True,  groundedness=0.8
  항목 2: recall_hit=False, groundedness=0.6
  항목 3: recall_hit=True,  groundedness=0.9
  → 집계: recall_at_k=0.667, groundedness=0.767, ...

【단일 책임 원칙】
이 모듈은 "집계 계산"만 담당합니다.
  - 평가 실행       → runner.py
  - 파일 저장 및 출력 → cli.py
"""

from .runner import ItemResult  # 평가 항목 결과 데이터 타입


def _mean(xs: list[float]) -> float:
    """숫자 리스트의 평균을 계산합니다.

    리스트가 비어있으면 ZeroDivisionError 가 발생하므로 0.0 을 반환합니다.

    Args:
        xs: 평균을 계산할 숫자 목록

    Returns:
        평균값, 또는 빈 리스트이면 0.0
    """
    # 리스트가 비어있지 않을 때만 계산합니다.
    return sum(xs) / len(xs) if xs else 0.0


def aggregate(results: list[ItemResult]) -> dict:
    """여러 평가 항목의 결과를 받아 전체 시스템 성능 요약 딕셔너리를 반환합니다.

    각 지표는 모든 항목의 평균값입니다.

    Args:
        results: runner.run_item() 이 반환한 ItemResult 객체 리스트

    Returns:
        지표 이름 → 평균값 딕셔너리:
            {
                "n"               : int,   # 평가 항목 수
                "recall_at_k"     : float, # 검색 hit 율 (0.0~1.0)
                "citation_rate"   : float, # 인용 번호 포함 비율
                "structure_rate"  : float, # ①②③ 구조 준수 비율
                "disclaimer_rate" : float, # 면책 문구 포함 비율
                "sources_rate"    : float, # 출처 존재 비율
                "mention_coverage": float, # 필수 키워드 커버리지 평균
                "groundedness"    : float, # LLM-as-Judge 근거성 점수 평균
            }
        results 가 비어있으면 {"n": 0} 만 반환합니다.
    """
    if not results:
        # 평가 항목이 없으면 빈 결과 반환 (ZeroDivisionError 방지)
        return {"n": 0}

    return {
        # 총 평가 항목 수
        "n": len(results),
        # recall_at_k : 검색 단계에서 기대 법조항을 찾은 비율
        # retrieval_hit=True 이면 1.0, False 이면 0.0 으로 변환 후 평균
        "recall_at_k": _mean([1.0 if r.retrieval_hit else 0.0 for r in results]),
        # citation_rate : 답변에 [n] 인용 번호가 있는 비율
        "citation_rate": _mean([1.0 if r.metrics["has_citation"] else 0.0 for r in results]),
        # structure_rate : 답변에 ①②③ 구조가 있는 비율
        "structure_rate": _mean([1.0 if r.metrics["has_structure"] else 0.0 for r in results]),
        # disclaimer_rate : 답변에 면책 문구가 있는 비율
        "disclaimer_rate": _mean([1.0 if r.metrics["has_disclaimer"] else 0.0 for r in results]),
        # sources_rate : 답변에 인용 출처가 1개 이상 있는 비율
        "sources_rate": _mean([1.0 if r.metrics["has_sources"] else 0.0 for r in results]),
        # mention_coverage : 필수 키워드 중 답변에 등장한 비율의 평균
        # 예: 항목마다 0.5, 1.0, 0.0 이면 평균 0.5
        "mention_coverage": _mean([r.metrics["mention_coverage"] for r in results]),
        # groundedness : LLM-as-Judge 근거성 점수의 평균 (0.0 ~ 1.0)
        "groundedness": _mean([r.groundedness for r in results]),
    }
