"""
main.py — FastAPI 애플리케이션 진입점(Entry Point)

【이 파일이 하는 일】
1. FastAPI 앱을 생성하고 미들웨어·엔드포인트를 등록합니다.
2. 의존성 주입(Dependency Injection) 패턴을 사용해 테스트 유연성을 확보합니다.
3. uvicorn 으로 서버를 실행할 때 이 파일의 `app` 객체를 사용합니다.

【엔드포인트 목록】
  GET  /health  → 서버 생존 확인 (헬스 체크)
  POST /chat    → 사용자 메시지를 받아 SSE 스트리밍으로 답변 반환

【SSE (Server-Sent Events) 란?】
서버가 클라이언트에 일방향으로 이벤트를 지속적으로 푸시하는 HTTP 프로토콜입니다.
WebSocket 보다 단순하며, LLM 처럼 토큰을 하나씩 보낼 때 자주 사용됩니다.

【의존성 주입 (Dependency Injection) 이란?】
객체가 필요한 외부 의존성(retriever, llm 등)을 직접 생성하지 않고,
외부에서 주입(파라미터로 전달)받는 설계 패턴입니다.
  - 실제 실행 : create_app()               → 실제 Retriever + MlxLLM 사용
  - 테스트    : create_app(llm=FakeLLM())  → 가짜 LLM 주입으로 빠른 테스트 가능

실행 방법:
    $ uvicorn api.main:app --reload
"""

import json  # Python 딕셔너리 ↔ JSON 문자열 변환 표준 라이브러리

from fastapi import FastAPI

# FastAPI : 고성능 웹 프레임워크. 타입 힌트 기반 자동 검증 및 문서 생성 기능 제공.
from fastapi.middleware.cors import CORSMiddleware

# CORSMiddleware : 브라우저의 동일 출처 정책(Same-Origin Policy)을 우회해
#   프론트엔드(localhost:3000)가 API 서버(localhost:8000)에 요청할 수 있게 합니다.
#   CORS = Cross-Origin Resource Sharing (교차 출처 리소스 공유)
from sse_starlette.sse import EventSourceResponse

# EventSourceResponse : HTTP 응답을 SSE 형식으로 스트리밍합니다.
#   일반 Response 는 응답 전체를 한 번에 보내지만,
#   EventSourceResponse 는 데이터를 준비되는 대로 조금씩 보냅니다.
from .pipeline import run_chat  # RAG 파이프라인 오케스트레이터
from .schemas import ChatRequest  # 요청 데이터 검증 모델
from .settings import Settings  # 전역 설정


# ══════════════════════════════════════════════════════════════
# 앱 팩토리 함수 (App Factory Function)
# 팩토리 패턴 : 객체 생성 로직을 한 함수에 캡슐화합니다.
# ══════════════════════════════════════════════════════════════
def create_app(
    retriever=None,  # 벡터 DB 검색 객체 (None 이면 서버 실행 시 자동 생성)
    llm=None,  # LLM 객체 (None 이면 서버 실행 시 자동 생성)
    settings: Settings | None = None,  # 설정 객체 (None 이면 환경 변수에서 로드)
) -> FastAPI:
    """FastAPI 앱 인스턴스를 생성하고 구성합니다.

    retriever 와 llm 을 직접 전달하면 테스트 시 가짜 구현체를 주입할 수 있습니다.
    전달하지 않으면 첫 요청 시 실제 구현체를 자동으로 생성합니다 (지연 로딩).

    Returns:
        설정이 완료된 FastAPI 앱 인스턴스
    """
    # FastAPI 앱 생성 (title 은 /docs Swagger UI 에 표시됩니다)
    app = FastAPI(title="보증금 반환 RAG 챗봇")

    # ── CORS 미들웨어 설정 ────────────────────────────────────
    # 미들웨어 : 모든 요청·응답을 가로채 공통 처리를 수행하는 레이어입니다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # 허용할 프론트엔드 주소
        allow_methods=["*"],  # 모든 HTTP 메서드 허용 (GET, POST, OPTIONS 등)
        allow_headers=["*"],  # 모든 HTTP 헤더 허용
    )

    # ── 앱 상태(State)에 의존성 저장 ─────────────────────────
    # app.state 는 앱 수명 동안 유지되는 전역 저장소입니다.
    # 라우트 핸들러에서 app.state.xxx 로 접근합니다.
    app.state.settings = settings or Settings.from_env()  # 설정 (or : None 이면 오른쪽 사용)
    app.state.retriever = retriever  # 검색 객체 (None 허용 → 첫 요청 시 생성)
    app.state.llm = llm  # LLM 객체 (None 허용 → 첫 요청 시 생성)

    # ── 엔드포인트 등록 ──────────────────────────────────────
    # @app.get("/health") : GET /health 요청을 이 함수가 처리합니다.
    @app.get("/health")
    def health():
        """서버가 정상 동작 중인지 확인하는 헬스 체크 엔드포인트.

        로드 밸런서, 쿠버네티스 등이 서버 생존 여부를 주기적으로 확인할 때 사용합니다.

        Returns:
            {"status": "ok"} — 항상 이 값을 반환합니다.
        """
        return {"status": "ok"}

    # @app.post("/chat") : POST /chat 요청을 이 함수가 처리합니다.
    @app.post("/chat")
    def chat(req: ChatRequest):
        """사용자 질문을 받아 RAG 파이프라인을 실행하고 SSE 스트림으로 답변합니다.

        FastAPI 가 req: ChatRequest 타입 힌트를 보고 자동으로:
          - 요청 바디 JSON → ChatRequest 객체 변환
          - 유효성 검증 (빈 message 등 거부)
          을 수행합니다.

        Args:
            req: ChatRequest 인스턴스 (message 필드 포함)

        Returns:
            EventSourceResponse: SSE 형식의 스트리밍 응답
        """
        # app.state.retriever 가 None 이면 (테스트 주입 없음) 실제 객체를 생성합니다.
        retr = app.state.retriever or _build_retriever(app.state.settings)
        # app.state.llm 이 None 이면 실제 MlxLLM 을 생성합니다.
        model = app.state.llm or _build_llm(app.state.settings)
        cfg = app.state.settings  # 설정 단축 참조

        def event_gen():
            """run_chat 의 이벤트 딕셔너리를 SSE 형식으로 변환하는 내부 제너레이터.

            SSE 이벤트는 {"data": "JSON 문자열"} 형태여야 합니다.
            ensure_ascii=False : 한글 등 비 ASCII 문자를 그대로 유지합니다.
            """
            for ev in run_chat(
                req.message,
                retriever=retr,
                llm=model,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
            ):
                # ev 는 {"type": "token", "text": ...} 같은 딕셔너리
                # json.dumps 로 문자열로 직렬화한 뒤 "data" 키에 담습니다.
                yield {"data": json.dumps(ev, ensure_ascii=False)}

        # EventSourceResponse 는 event_gen() 제너레이터를 받아
        # SSE 프로토콜에 맞는 HTTP 스트리밍 응답을 만들어 줍니다.
        return EventSourceResponse(event_gen())

    return app


# ══════════════════════════════════════════════════════════════
# 지연 로딩(Lazy Loading) 헬퍼 함수들
# 함수 속성(_cached)을 이용한 간단한 싱글턴(Singleton) 패턴입니다.
# 함수가 처음 호출될 때만 객체를 생성하고, 이후에는 캐시된 객체를 재사용합니다.
# ══════════════════════════════════════════════════════════════
def _build_retriever(settings: Settings):
    """Retriever 인스턴스를 처음 한 번만 생성하고 캐시합니다.

    Retriever 는 벡터 DB 를 메모리에 로드하므로 생성 비용이 비쌉니다.
    싱글턴으로 관리해 중복 생성을 방지합니다.
    """
    from rag.retriever import Retriever  # 지연 import (무거운 패키지이므로)

    # hasattr(obj, name) : obj 가 name 속성을 가지고 있으면 True 반환
    # 함수 자체에 _cached 속성이 없으면 (= 처음 호출) Retriever 를 생성합니다.
    if not hasattr(_build_retriever, "_cached"):
        _build_retriever._cached = Retriever(settings.rag)
    return _build_retriever._cached  # 캐시된 인스턴스 반환


def _build_llm(settings: Settings):
    """MlxLLM 인스턴스를 처음 한 번만 생성하고 캐시합니다.

    LLM 모델 로딩은 수 GB 의 파일을 메모리에 올리는 작업이므로 시간이 많이 걸립니다.
    싱글턴으로 관리해 요청마다 재로딩하는 것을 방지합니다.
    """
    from .llm import MlxLLM  # 지연 import (Apple Silicon 환경에서만 동작)

    if not hasattr(_build_llm, "_cached"):
        _build_llm._cached = MlxLLM(settings.mlx_model)
    return _build_llm._cached


# ──────────────────────────────────────────────────────────
# 모듈 최상위 앱 인스턴스 생성
#
# uvicorn api.main:app 명령으로 서버를 실행할 때 이 app 객체를 사용합니다.
# create_app() 을 호출하지만, retriever/llm 은 None 으로 전달합니다.
# 실제 Retriever 와 MlxLLM 은 첫 번째 /chat 요청 시 지연 생성됩니다.
# ──────────────────────────────────────────────────────────
app = create_app()  # uvicorn api.main:app 용 (실제 구성, 지연 로딩)
