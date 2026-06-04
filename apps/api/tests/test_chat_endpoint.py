import json

from fastapi.testclient import TestClient

from api.main import create_app
from api.llm import FakeLLM
from rag.types import Retrieved


class StubRetriever:
    def retrieve(self, query):
        return [Retrieved(id="i1", text="임차인은 보증금을 우선변제 받는다",
                          similarity=0.7, source_type="법령",
                          title="주택임대차보호법 제3조의2", ref="제3조의2",
                          url="https://law/1", date="2023-07-19")]
    def is_grounded(self, hits):
        return True


def _client():
    app = create_app(retriever=StubRetriever(),
                     llm=FakeLLM(["보증금은 ", "우선변제[1] 됩니다."]))
    return TestClient(app)


def test_health():
    assert _client().get("/health").json() == {"status": "ok"}


def test_chat_streams_sse_tokens_and_done():
    with _client() as client:
        with client.stream("POST", "/chat", json={"message": "보증금?"}) as resp:
            assert resp.status_code == 200
            body = "".join(resp.iter_text())
    payloads = [json.loads(line[len("data: "):])
                for line in body.splitlines() if line.startswith("data: ")]
    types = [p["type"] for p in payloads]
    assert types[-1] == "done"
    done = payloads[-1]
    assert "우선변제" in done["answer"]
    assert done["sources"][0]["url"] == "https://law/1"


def test_chat_rejects_empty_message():
    assert _client().post("/chat", json={"message": ""}).status_code == 422
