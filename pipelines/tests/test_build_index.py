import json

from pipelines.index.build_index import COLLECTION, build_index


def _write_chunks(path, chunks):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def test_build_index_adds_all_chunks(tmp_path):
    chunks_path = tmp_path / "chunks.jsonl"
    _write_chunks(chunks_path, [
        {"id": "law-1", "text": "임차인은 보증금을 ...", "source_type": "법령",
         "title": "주택임대차보호법 제3조의2", "ref": "제3조의2", "url": "u", "date": "2023-07-19"},
        {"id": "prec-1", "text": "동시이행 관계 ...", "source_type": "판례",
         "title": "대법원 2020다1", "ref": "판결요지", "url": "u", "date": "2021-01-15"},
    ])

    # 결정적 가짜 임베딩(텍스트 길이 기반 2차원)
    def fake_encode(texts):
        return [[float(len(t)), 1.0] for t in texts]

    count = build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma",
                        encode_fn=fake_encode)
    assert count == 2

    import chromadb
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    col = client.get_collection(COLLECTION)
    assert col.count() == 2

    got = col.get(ids=["law-1"], include=["metadatas", "documents"])
    assert got["documents"][0].startswith("임차인은")
    assert got["metadatas"][0]["source_type"] == "법령"


def test_build_index_is_idempotent(tmp_path):
    chunks_path = tmp_path / "chunks.jsonl"
    _write_chunks(chunks_path, [
        {"id": "law-1", "text": "a", "source_type": "법령",
         "title": "t", "ref": "r", "url": "u", "date": "2023-01-01"},
    ])
    def fn(texts):
        return [[1.0, 0.0] for _ in texts]
    build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma", encode_fn=fn)
    build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma", encode_fn=fn)

    import chromadb
    col = chromadb.PersistentClient(path=str(tmp_path / "chroma")).get_collection(COLLECTION)
    assert col.count() == 1     # 중복 삽입 없음(upsert)
