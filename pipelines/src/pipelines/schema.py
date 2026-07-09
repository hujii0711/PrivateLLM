from typing import Literal, TypedDict

SOURCE_TYPES = ("법령", "판례", "해설", "상담사례")
# Python의 타입 힌트로, 변수가 가질 수 있는 값을 특정 문자열로 제한한다는 것을 표현합니다.
# 이 타입은 "이 변수는 반드시 "법령", "판례", "해설", "상담사례" 중 하나여야 한다"는 뜻입니다.
SourceType = Literal["법령", "판례", "해설", "상담사례"]


# TypedDict 상속 — "이 딕셔너리의 키/값 타입은 이렇다"는 선언
# 겉모습은 상속이지만, 실제 의미는 "이 구조를 가진 딕셔너리 타입을 정의한다" 는 선언입니다.
# Chunk로 만든 객체는 실제로는 그냥 dict 입니다. TypedDict는 런타임에 영향을 주지 않고, 타입 체커에게 구조 정보를 알려주는 역할만 합니다.
class Chunk(TypedDict):
    """검색 색인에 넣는 최소 문서 단위의 공통 스키마.

    법령, 판례, 해설, 상담사례처럼 원천은 달라도 색인 단계 이후에는
    동일한 필드 구조로 다루기 위해 사용한다. `text`는 임베딩 대상 본문이고,
    나머지 필드는 검색 결과에서 출처와 근거를 보여주기 위한 메타데이터다.
    """

    id: str  # 인스턴스 변수가 아니라 키 선언
    text: str
    source_type: SourceType
    title: str
    ref: str
    url: str
    date: str


def make_chunk(
    *, id: str, text: str, source_type: str, title: str, ref: str, url: str, date: str
) -> Chunk:
    """Chunk를 생성하면서 지원하는 source_type인지 검증한다.

    여러 파이프라인 단계에서 직접 dict를 만들면 출처 타입 오타가 색인까지
    흘러갈 수 있으므로, 이 함수가 Chunk 생성의 작은 관문 역할을 한다.
    """
    # not in은 "컬렉션 안에 없으면 True" 를 반환합니다.
    # SOURCE_TYPES 는 ( "법령", "판례", "해설", "상담사례" ) 이므로, source_type 이 이 네 개 중 하나가 아니면 에러를 발생시킵니다.

    if source_type not in SOURCE_TYPES:
        # raise: 예외를 강제로 발생시키는 키워드
        # ValueError: 값이 잘못됐을 때 사용하는 예외 종류
        # !r은 값을 따옴표와 함께 출력합니다. ex) hello -> 'hello'
        raise ValueError(f"unknown source_type: {source_type!r}")
    return Chunk(
        id=id, text=text, source_type=source_type, title=title, ref=ref, url=url, date=date
    )


# 결과물의 정체
# chunk = Chunk(id="001", text="본문")

# type(chunk)        # <class 'dict'>  ← 일반 딕셔너리
# isinstance(chunk, dict)  # True

# # 딕셔너리처럼 사용
# chunk["id"]        # "001"
# chunk["text"]      # "본문"
