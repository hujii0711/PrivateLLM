import pytest

from pipelines.index.embedder import Embedder


def test_embed_uses_injected_encoder():
    calls = {}

    def fake_encode(texts):
        calls["texts"] = list(texts)
        return [[0.1, 0.2], [0.3, 0.4]]

    emb = Embedder(encode_fn=fake_encode)
    vecs = emb.embed(["가", "나"])
    assert vecs == [[0.1, 0.2], [0.3, 0.4]]
    assert calls["texts"] == ["가", "나"]


def test_embed_empty_returns_empty():
    emb = Embedder(encode_fn=lambda t: [])
    assert emb.embed([]) == []


@pytest.mark.slow
def test_real_bge_m3_dimension():
    emb = Embedder()  # 실제 모델 로딩
    vecs = emb.embed(["보증금 반환 청구"])
    assert len(vecs) == 1
    assert len(vecs[0]) == 1024     # bge-m3 dense 차원
