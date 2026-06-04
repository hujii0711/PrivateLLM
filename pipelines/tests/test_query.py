from pipelines.index.build_index import build_index
from pipelines.cli.query import search


def test_search_returns_topk_with_metadata(tmp_path):
    import json
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {"id": "a", "text": "보증금 반환 청구", "source_type": "법령",
         "title": "주택임대차보호법 제3조의2", "ref": "제3조의2", "url": "u1", "date": "2023-07-19"},
        {"id": "b", "text": "임대차 기간", "source_type": "법령",
         "title": "주택임대차보호법 제4조", "ref": "제4조", "url": "u2", "date": "2023-07-19"},
    ]
    with chunks_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 텍스트에 '보증금' 포함 시 첫 축을 크게 → 질의와 가깝게
    def fake_encode(texts):
        return [[1.0, 0.0] if "보증금" in t else [0.0, 1.0] for t in texts]

    build_index(chunks_path=chunks_path, chroma_dir=tmp_path / "chroma", encode_fn=fake_encode)

    results = search("보증금을 못 받았어요", chroma_dir=tmp_path / "chroma",
                     encode_fn=fake_encode, k=1)
    assert len(results) == 1
    assert results[0]["id"] == "a"
    assert results[0]["title"].startswith("주택임대차보호법")
    assert "보증금" in results[0]["text"]
