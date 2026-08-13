"""학습 후보 형식 필터 — 평가의 answer_metrics를 재사용해 품질 기준을 일치시킨다.
--> 4가지 품질 조건(has_citation, has_structure, has_disclaimer, has_sources) 각각 설명

이 모듈은 LLM이 생성한 후보 답변이 파인튜닝 학습에 쓸 수 있을 만큼
형식 요건을 갖췄는지 걸러내는(필터링하는) 역할을 합니다.

평가(eval) 모듈의 answer_metrics 함수를 그대로 재사용함으로써,
학습 데이터와 평가 기준이 동일한 품질 잣대를 사용하도록 보장합니다.
"""

from eval.answer_metrics import answer_metrics  # 답변 품질 지표를 계산하는 함수


def format_ok(answer: str, *, sources: list) -> bool:
    """후보 답변이 파인튜닝 학습에 사용 가능한 형식 요건을 모두 만족하는지 검사합니다.

    아래 4가지 조건을 모두 충족해야 True를 반환합니다:
      1. has_citation   : 답변 안에 "[1]", "[2]" 같은 각주(인용) 표기가 있는가?
      2. has_structure  : 상담형 답변 구조(도입부·본문·결론 등)를 갖췄는가?
      3. has_disclaimer : 법적 면책 고지(예: "전문가와 상담하세요")가 포함됐는가?
      4. has_sources    : 출처 목록(참고 문서 링크 등)이 명시됐는가?

    Args:
        answer:  검사할 LLM 생성 답변 텍스트.
        sources: 답변에 사용된 출처 문서 목록 (must_mention 검사에 활용됨).

    Returns:
        4가지 조건을 모두 만족하면 True, 하나라도 부족하면 False.
    """
    # answer_metrics()는 답변 품질 지표를 딕셔너리로 반환합니다.
    # must_mention=[] 이므로 "반드시 언급해야 할 키워드" 검사는 생략합니다.
    m = answer_metrics(answer, sources=sources, must_mention=[])

    # 4가지 조건을 AND로 연결 — 하나라도 False면 전체가 False가 됩니다.
    return (
        m["has_citation"]  # [n] 형식의 인용이 있어야 함
        and m["has_structure"]  # 상담형 구조를 갖춰야 함
        and m["has_disclaimer"]  # 법적 면책 고지가 있어야 함
        and m["has_sources"]  # 출처 목록이 명시돼야 함
    )
