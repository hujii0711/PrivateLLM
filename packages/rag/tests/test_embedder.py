import pytest

from rag.embedder import QueryEmbedder


def test_embeds_with_injected_fn():
    emb = QueryEmbedder(encode_fn=lambda texts: [[0.5, 0.5] for _ in texts])
    assert emb.embed_query("보증금 반환") == [0.5, 0.5]


@pytest.mark.slow
def test_real_bge_m3_dim():
    emb = QueryEmbedder()
    v = emb.embed_query("전세 보증금을 못 받았어요")
    assert len(v) == 1024
