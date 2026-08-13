"""
answer_metrics.py — LLM 답변의 형식·내용 품질을 측정하는 지표 계산 모듈

【결정적(Deterministic) 지표란?】
LLM 이 아닌, 규칙 기반(정규식, 문자열 검사)으로 계산하는 지표입니다.
입력이 같으면 항상 같은 결과가 나오므로 빠르고 재현 가능합니다.
(vs LLM-as-judge : 확률적, 느림, 비쌈 → judge.py 참조)

【측정하는 지표들】
  has_citation   : [1], [2] 형식의 인용 번호가 하나라도 있는가?
  has_structure  : ①②③ 형식의 답변 구조(상황요약·적용법리·다음절차)를 갖췄는가?
  has_disclaimer : "법률 자문이 아닙니다" 면책 문구가 있는가?
  has_sources    : 인용된 출처가 하나라도 있는가?
  mention_coverage: must_mention 키워드 중 몇 %가 답변에 등장했는가?
"""

import re  # 정규식(Regular Expression) 표준 라이브러리

# ──────────────────────────────────────────────────────────
# 검사 패턴 및 상수
# ──────────────────────────────────────────────────────────

# [1], [23] 같은 인용 번호 패턴을 찾는 정규식
# \[ : 리터럴 [  \d+ : 하나 이상의 숫자  \] : 리터럴 ]
_CITE = re.compile(r"\[\d+\]")

# 답변 구조 마커 (상담형 3단계 형식)
# 시스템 프롬프트에서 ① 상황 요약, ② 적용 법리, ③ 다음 절차 형식을 요구합니다.
_STRUCT = ("①", "②", "③")

# 면책 문구의 핵심 부분 (전체 문장이 아닌 일부로 검사해 변형에 유연하게 대응)
_DISCLAIMER = "법률 자문이 아닙니다"


def answer_metrics(
    answer: str,         # 검사할 LLM 답변 텍스트
    *,                   # 이후 인자는 반드시 키워드 인자로 전달
    sources: list,       # extract_sources() 가 반환한 출처 목록
    must_mention: list[str],  # 답변에 반드시 등장해야 할 키워드 목록
) -> dict:
    """LLM 답변의 형식·내용 준수 여부를 규칙 기반으로 측정합니다.

    Args:
        answer        : LLM 이 생성한 최종 답변 텍스트
        sources       : 답변에서 추출된 인용 출처 목록 (비어있으면 출처 없음)
        must_mention  : 이 질문에서 반드시 언급되어야 할 키워드 목록
                        (EvalItem.must_mention 에서 가져옴)

    Returns:
        지표 이름 → 측정 결과 딕셔너리:
            {
                "has_citation"     : bool,   # 인용 번호 존재 여부
                "has_structure"    : bool,   # ①②③ 구조 준수 여부
                "has_disclaimer"   : bool,   # 면책 문구 포함 여부
                "has_sources"      : bool,   # 출처 목록 비어있지 않음 여부
                "mention_coverage" : float,  # 필수 키워드 커버리지 (0.0~1.0)
            }
    """
    # _CITE.search(answer) : 답변 어딘가에 [n] 패턴이 있으면 Match 객체 반환, 없으면 None
    # bool(...) : Match 객체이면 True, None 이면 False
    has_citation = bool(_CITE.search(answer))

    # all(iterable) : 모든 요소가 True 이면 True
    # ①, ②, ③ 세 마커가 모두 답변에 있어야 구조를 갖춘 것으로 판단합니다.
    has_structure = all(mark in answer for mark in _STRUCT)

    # "법률 자문이 아닙니다" 문자열이 답변에 있는지 확인합니다.
    has_disclaimer = _DISCLAIMER in answer

    # 출처 목록이 비어있지 않으면 True
    has_sources = len(sources) > 0

    # 필수 키워드 커버리지 계산
    if must_mention:
        # 각 키워드(kw)가 답변에 있으면 1, 없으면 0 으로 계산
        hit = sum(1 for kw in must_mention if kw in answer)
        # hit 수 / 전체 키워드 수 = 커버리지 비율 (0.0 ~ 1.0)
        coverage = hit / len(must_mention)
    else:
        # must_mention 이 빈 리스트이면 평가 기준 없음 → 1.0 (만점)
        coverage = 1.0

    return {
        "has_citation": has_citation,
        "has_structure": has_structure,
        "has_disclaimer": has_disclaimer,
        "has_sources": has_sources,
        "mention_coverage": coverage,
    }
