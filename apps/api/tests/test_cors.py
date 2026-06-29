from fastapi.testclient import TestClient

from api.llm import FakeLLM
from api.main import create_app


class StubRetriever:
    def retrieve(self, q): return []
    def is_grounded(self, h): return False


def test_cors_allows_localhost_3000():
    app = create_app(retriever=StubRetriever(), llm=FakeLLM([]))
    client = TestClient(app)
    resp = client.options(
        "/chat",
        headers={"Origin": "http://localhost:3000",
                 "Access-Control-Request-Method": "POST"},
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
