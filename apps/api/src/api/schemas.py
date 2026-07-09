"""
schemas.py — API 요청/응답 데이터 형식(Schema) 정의 모듈

Pydantic 라이브러리를 사용해 데이터 모델을 선언합니다.
FastAPI 는 이 모델을 이용해 다음 작업을 자동으로 수행합니다:
  1. 요청 데이터 파싱  : JSON → Python 객체 변환
  2. 유효성 검증      : 타입 오류, 필드 누락, 범위 초과 등을 자동 감지
  3. 문서 자동 생성   : /docs (Swagger UI) 에서 바로 API 스펙 확인 가능

【Pydantic 이란?】
파이썬 타입 힌트를 기반으로 데이터 검증을 수행하는 라이브러리입니다.
잘못된 데이터가 들어오면 ValidationError 를 발생시켜 버그를 조기에 잡아줍니다.
"""

from pydantic import BaseModel, Field

# BaseModel : Pydantic 모델의 부모 클래스. 상속받으면 자동 검증 기능이 활성화됩니다.
# Field     : 필드에 추가 제약 조건(최소 길이, 최대 길이, 설명 등)을 붙일 때 사용합니다.


# ──────────────────────────────────────────────────────────
# ChatRequest — 채팅 엔드포인트(/chat)에 전달되는 요청 바디
# ──────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    """클라이언트(프론트엔드)가 /chat 에 POST 할 때 보내는 JSON 형식.

    예시 요청 JSON:
        {"message": "보증금 반환 절차가 어떻게 되나요?"}

    검증 규칙:
        - message 필드는 반드시 존재해야 합니다.
        - 빈 문자열("")은 허용되지 않습니다 (min_length=1).
    """

    # Field(min_length=1) : 문자열 길이가 1 미만이면 422 Unprocessable Entity 오류를 반환합니다.
    # 즉, 사용자가 아무것도 입력하지 않고 전송하는 것을 서버 단에서 막습니다.
    message: str = Field(min_length=1)


# ──────────────────────────────────────────────────────────
# SourceOut — /chat 응답에 포함되는 출처(인용 문헌) 형식
# ──────────────────────────────────────────────────────────
class SourceOut(BaseModel):
    """LLM 답변에서 인용된 법령·판례 등의 출처 정보.

    /chat 응답의 "sources" 배열 안에 이 형식의 객체가 들어갑니다.

    예시:
        {
            "n": 1,
            "title": "주택임대차보호법 제3조의3",
            "ref": "[1]",
            "url": "https://www.law.go.kr/...",
            "source_type": "law"
        }
    """

    n: int  # 인용 번호 (답변 본문의 [1], [2] 와 대응)
    title: str  # 법령명, 판례명 등 출처의 제목
    ref: str  # 본문에서 사용한 참조 표기 (예: "[1]")
    url: str  # 원문 링크 (법령 정보 사이트, 판례 DB 등)
    source_type: str  # 출처 유형 (예: "law" = 법령, "case" = 판례)
