from rag.config import RagConfig
from rag.retriever import Retriever


def test_retrieves_topk_ordered(fake_chroma, fake_encode):
    cfg = RagConfig(chroma_dir=fake_chroma, top_k=2, min_similarity=0.1)
    r = Retriever(cfg, encode_fn=fake_encode)
    hits = r.retrieve("보증금을 못 받았어요")
    assert len(hits) == 2
    assert hits[0].id == "law-1"             # '보증금' 청크가 1위
    assert hits[0].title.startswith("주택임대차보호법")
    assert 0.0 <= hits[0].similarity <= 1.0
    assert hits[0].similarity >= hits[1].similarity


def test_is_grounded_true_when_strong_hit(fake_chroma, fake_encode):
    cfg = RagConfig(chroma_dir=fake_chroma, top_k=3, min_similarity=0.5)
    r = Retriever(cfg, encode_fn=fake_encode)
    hits = r.retrieve("보증금 우선변제")
    assert r.is_grounded(hits) is True       # 완전 일치(유사도 1.0) 존재


def test_is_grounded_false_when_all_weak(fake_chroma, fake_encode):
    # 질의에 '보증금'이 없으면 fake_encode가 [0,1] → '보증금' 청크와 직교(유사도 0)
    cfg = RagConfig(chroma_dir=fake_chroma, top_k=3, min_similarity=0.5)
    r = Retriever(cfg, encode_fn=fake_encode)
    hits = r.retrieve("날씨가 좋네요")
    assert r.is_grounded(hits) is False
