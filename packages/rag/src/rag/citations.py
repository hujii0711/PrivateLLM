"""
citations.py — LLM 답변의 인용 번호([n])를 검증하고 출처 목록을 만드는 모듈

【이 파일이 필요한 이유: LLM 환각(Hallucination) 방지】
LLM 은 때때로 실제로 없는 인용 번호를 꾸며냅니다.
예를 들어 검색 결과가 3개([1]~[3])뿐인데,
LLM 이 "[5]" 나 "[99]" 를 답변에 포함시킬 수 있습니다.

이 모듈은 두 가지 방어를 수행합니다:
  1. strip_invalid_citations : 답변 텍스트에서 유효 범위를 벗어난 [n] 을 제거
  2. extract_sources         : 실제로 존재하고 유효한 인용 번호만 출처 목록으로 반환

처리 순서 (pipeline.py 에서 호출):
  raw 답변 → strip_invalid_citations() → 정리된 답변
          → extract_sources()           → 인용 출처 목록
          → _ensure_disclaimer()        → 면책 문구 추가
          → 최종 응답

【정규식(Regular Expression)이란?】
텍스트 패턴을 표현하는 언어입니다.
  r"\\[(\\d+)\\]"
    \\[  : 리터럴 대괄호 [  (정규식에서 [ 는 특수문자라 \\ 로 이스케이프)
    (    : 캡처 그룹 시작 (괄호 안의 내용을 나중에 꺼낼 수 있음)
    \\d+ : 하나 이상의 숫자 (\\d = digit)
    )    : 캡처 그룹 끝
    \\]  : 리터럴 대괄호 ]
  → "[1]", "[23]", "[100]" 같은 패턴을 찾습니다.
"""

import re  # 정규식(Regular Expression) 표준 라이브러리

from .types import Retrieved, Source  # 공유 데이터 타입

# 컴파일된 정규식 패턴 객체
# re.compile() 로 미리 컴파일해두면 반복 호출 시 성능이 향상됩니다.
# r"..." : raw string. \n, \t 등이 이스케이프 시퀀스로 해석되지 않습니다.
_CITE = re.compile(r"\[(\d+)\]")
# 이 패턴은 "[1]", "[23]" 같은 인용 번호를 찾고,
# 내부 숫자를 캡처 그룹 1번 (group(1)) 으로 꺼낼 수 있습니다.


def extract_sources(answer: str, hits: list[Retrieved]) -> list[Source]:
    """LLM 답변에서 실제로 사용된 유효한 인용 번호를 Source 목록으로 반환합니다.

    유효 인용: 1 이상, len(hits) 이하인 번호 (실제 검색 결과 범위 안)
    등장 순서대로 반환하며, 같은 번호가 여러 번 등장해도 1번만 포함합니다.

    예:
        hits 가 3개이고, 답변이 "...합니다[1]. ...입니다[2]. ...합니다[1]." 인 경우
        → [Source(n=1, ...), Source(n=2, ...)]  ← 중복 제거, 등장 순서 유지

    Args:
        answer : LLM 이 생성한 최종 답변 텍스트 (인용 번호 포함)
        hits   : retriever.retrieve() 가 반환한 검색 결과 리스트

    Returns:
        답변에서 실제로 인용된 출처 정보 리스트 (등장 순서, 중복 없음)
    """
    seen: set[int] = set()  # 이미 처리한 번호를 기억하는 집합 (중복 방지)
    sources: list[Source] = []  # 결과를 담을 리스트

    # _CITE.finditer(answer) : 답변 텍스트에서 [n] 패턴을 왼쪽→오른쪽 순서로 모두 찾음
    for m in _CITE.finditer(answer):
        n = int(m.group(1))  # 캡처 그룹 1번 (괄호 안 숫자) 을 정수로 변환

        # 유효 범위 확인: 1 이상이고 검색 결과 개수 이하
        # 이미 처리한 번호(seen) 가 아닌 경우만 추가
        if 1 <= n <= len(hits) and n not in seen:
            seen.add(n)  # 처리 완료 표시
            h = hits[n - 1]  # n은 1-indexed, 리스트는 0-indexed이므로 n-1

            # Retrieved 에서 Source 로 변환 (본문 텍스트 제외, 출처 정보만)
            sources.append(
                Source(
                    n=n,
                    title=h.title,
                    ref=h.ref,
                    url=h.url,
                    source_type=h.source_type,
                )
            )
    return sources


def strip_invalid_citations(answer: str, hits: list[Retrieved]) -> str:
    """답변 텍스트에서 유효 범위를 벗어난 환각 인용 번호를 제거합니다.

    LLM 이 "[99]" 처럼 존재하지 않는 번호를 생성한 경우,
    해당 "[99]" 문자열을 답변에서 완전히 삭제합니다.
    유효한 번호(1 ~ len(hits))는 그대로 유지됩니다.

    Args:
        answer : LLM 이 생성한 원본 답변 텍스트
        hits   : retriever.retrieve() 가 반환한 검색 결과 리스트

    Returns:
        환각 인용 번호가 제거된 정리된 답변 텍스트
    """

    def repl(m) -> str:
        """정규식이 찾은 [n] 패턴 하나에 대한 대체 함수.

        Args:
            m: 정규식 매치(match) 객체

        Returns:
            유효한 번호이면 원래 텍스트("[n]") 그대로,
            범위를 벗어난 번호이면 빈 문자열("") 반환 → 삭제 효과
        """
        n = int(m.group(1))
        # 유효하면 그대로 (m.group(0) = "[n]" 전체 문자열)
        # 무효하면 빈 문자열로 교체 → 텍스트에서 삭제
        return m.group(0) if 1 <= n <= len(hits) else ""

    # re.sub(pattern, repl, string) : pattern 에 매치되는 부분을 repl 함수 결과로 교체
    # _CITE.sub(repl, answer) 는 _CITE 패턴으로 answer 를 스캔하며
    # 매치될 때마다 repl() 함수를 호출해 교체합니다.
    return _CITE.sub(repl, answer)
