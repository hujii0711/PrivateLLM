import chromadb
import pytest


@pytest.fixture
def fake_chroma(tmp_path):
    """결정적 3차원 가짜 임베딩으로 채운 임시 Chroma 컬렉션 경로를 돌려준다.

    임베딩 규칙: '보증금'→[1,0,0], '날씨'→[0,1,0], 그 외→[0,0,1].
    질의도 같은 규칙으로 임베딩하면 '보증금' 청크가 가깝게 검색되고,
    어느 키워드도 없는 질의는 모든 청크와 직교(유사도 0)가 된다.
    """
    from rag.config import COLLECTION  # 지연 import: Task 1 전 수집 단계가 깨지지 않게

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    rows = [
        ("law-1", "임차인은 보증금을 우선변제 받을 수 있다", "법령",
         "주택임대차보호법 제3조의2(보증금의 회수)", "제3조의2", "https://law/1", "2023-07-19"),
        ("law-2", "임대차 기간은 2년으로 본다", "법령",
         "주택임대차보호법 제4조(임대차기간)", "제4조", "https://law/2", "2023-07-19"),
        ("prec-1", "보증금 반환과 주택 인도는 동시이행 관계이다", "판례",
         "대법원 2020다1 임차보증금반환", "판결요지", "https://law/p1", "2021-01-15"),
    ]
    def emb(t):
        if "보증금" in t:
            return [1.0, 0.0, 0.0]
        if "날씨" in t:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]
    col.add(
        ids=[r[0] for r in rows],
        documents=[r[1] for r in rows],
        embeddings=[emb(r[1]) for r in rows],
        metadatas=[{"source_type": r[2], "title": r[3], "ref": r[4],
                    "url": r[5], "date": r[6]} for r in rows],
    )
    return tmp_path / "chroma"


@pytest.fixture
def fake_encode():
    """conftest의 fake_chroma와 동일한 임베딩 규칙."""
    def _emb(t):
        if "보증금" in t:
            return [1.0, 0.0, 0.0]
        if "날씨" in t:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    def _encode(texts):
        return [_emb(t) for t in texts]
    return _encode
