"""FastAPI 앱: POST /chat (SSE 스트리밍), GET /health.

create_app(retriever=, llm=)로 의존성을 주입(테스트). 미주입 시 실제 구성."""
import json

from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

from .pipeline import run_chat
from .schemas import ChatRequest
from .settings import Settings


def create_app(retriever=None, llm=None, settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="보증금 반환 RAG 챗봇")
    app.state.settings = settings or Settings.from_env()
    app.state.retriever = retriever
    app.state.llm = llm

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/chat")
    def chat(req: ChatRequest):
        retr = app.state.retriever or _build_retriever(app.state.settings)
        model = app.state.llm or _build_llm(app.state.settings)
        cfg = app.state.settings

        def event_gen():
            for ev in run_chat(req.message, retriever=retr, llm=model,
                               max_tokens=cfg.max_tokens, temperature=cfg.temperature):
                yield {"data": json.dumps(ev, ensure_ascii=False)}

        return EventSourceResponse(event_gen())

    return app


def _build_retriever(settings: Settings):
    from rag.retriever import Retriever
    if not hasattr(_build_retriever, "_cached"):
        _build_retriever._cached = Retriever(settings.rag)
    return _build_retriever._cached


def _build_llm(settings: Settings):
    from .llm import MlxLLM
    if not hasattr(_build_llm, "_cached"):
        _build_llm._cached = MlxLLM(settings.mlx_model)
    return _build_llm._cached


app = create_app()  # uvicorn api.main:app 용 (실제 구성, 지연 로딩)
