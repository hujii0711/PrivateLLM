"""
types.py — RAG 파이프라인에서 사용하는 공유 데이터 타입 정의

【이 파일의 역할】
여러 모듈(retriever, citations, prompt 등)에서 공통으로 사용하는
데이터 구조(클래스)를 한 곳에 모아 정의합니다.
타입을 분리하면:
  - 순환 import(circular import) 문제를 방지할 수 있습니다.
  - 각 모듈이 "어떤 형태의 데이터를 받고 반환하는지" 명확해집니다.

【@dataclass 란?】
파이썬 3.7+ 에서 제공하는 기능으로, 순수하게 데이터를 담는 클래스를
간결하게 선언할 수 있습니다.
@dataclass 를 붙이면 __init__, __repr__, __eq__ 메서드가 자동 생성됩니다.

    # 직접 작성하면 이렇게 길어집니다:
    class Retrieved:
        def __init__(self, id, text, similarity, ...):
            self.id = id
            self.text = text
            ...

    # @dataclass 를 쓰면 이렇게 간결합니다:
    @dataclass
    class Retrieved:
        id: str
        text: str
        ...
"""

from dataclasses import dataclass  # 데이터클래스 데코레이터


# ══════════════════════════════════════════════════════════════
# Retrieved — 벡터 DB 검색 결과 1건
# ══════════════════════════════════════════════════════════════
@dataclass
class Retrieved:
    """ChromaDB 에서 검색된 문서 1건의 데이터.

    retriever.retrieve(query) 가 반환하는 리스트의 각 원소입니다.

    Attributes:
        id          : ChromaDB 내부 문서 고유 ID
        text        : 실제 법령·판례 본문 텍스트 (LLM 프롬프트에 포함됨)
        similarity  : 질문 벡터와의 코사인 유사도 (0.0 ~ 1.0)
                      1에 가까울수록 질문과 의미적으로 유사합니다.
        source_type : 출처 유형 (예: "law" = 법령, "case" = 판례)
        title       : 법조항명·판례명 등 출처 제목 (예: "주택임대차보호법 제3조의3")
        ref         : 본문 인용에 쓰이는 짧은 참조 코드 (예: "제3조의3")
        url         : 원문을 볼 수 있는 외부 링크 URL
        date        : 법령 시행일 또는 판례 선고일 (문자열)
    """

    id: str              # ChromaDB 문서 고유 식별자
    text: str            # 검색된 문서 본문 (LLM에게 "근거"로 제공되는 내용)
    similarity: float    # 코사인 유사도: 1.0 - ChromaDB distance (거리 → 유사도로 변환)
    source_type: str     # 출처 유형 식별자 ("law", "case" 등)
    title: str           # 사람이 읽기 쉬운 출처 제목
    ref: str             # 인용 코드 (예: "제3조의3", "대법원 2021다12345")
    url: str             # 원문 외부 링크
    date: str            # 시행일 또는 선고일


# ══════════════════════════════════════════════════════════════
# Source — API 응답에 포함되는 최종 인용 출처
# ══════════════════════════════════════════════════════════════
@dataclass
class Source:
    """LLM 답변에서 실제로 인용된 출처 정보.

    Retrieved 와의 차이:
        Retrieved : 검색 단계에서 가져온 "후보" 문서 (본문 텍스트 포함)
        Source    : 최종 답변에서 실제로 인용된 출처만 추출한 것 (본문 제외)

    citations.extract_sources() 함수가 답변 텍스트의 [1], [2] 번호를
    실제 Retrieved 와 매핑해 Source 목록을 만들어 줍니다.

    Attributes:
        n           : 답변 본문에 등장한 인용 번호 (예: [1] → n=1)
        title       : 출처 제목
        ref         : 짧은 참조 코드
        url         : 원문 링크
        source_type : 출처 유형
    """

    n: int              # 인용 번호 [n] — 답변 본문의 [1], [2] 와 1:1 대응
    title: str          # 출처 제목
    ref: str            # 짧은 참조 코드
    url: str            # 원문 외부 링크
    source_type: str    # 출처 유형
