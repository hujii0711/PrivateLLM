"""검색 스모크 CLI: 질의 → top-k 청크."""
import sys
from pathlib import Path

import chromadb

from ..index.build_index import COLLECTION
from ..index.embedder import Embedder


def search(query: str, *, chroma_dir: Path, encode_fn=None, k: int = 6) -> list[dict]:
    embedder = Embedder(encode_fn=encode_fn)
    qvec = embedder.embed([query])[0]
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_collection(COLLECTION)
    res = col.query(query_embeddings=[qvec], n_results=k,
                    include=["documents", "metadatas", "distances"])
    out = []
    for id_, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                    res["metadatas"][0], res["distances"][0]):
        out.append({"id": id_, "text": doc, "distance": dist, **meta})
    return out


def main() -> None:
    from ..config import Config

    if len(sys.argv) < 2:
        print('사용법: uv run python -m pipelines.cli.query "질문"')
        raise SystemExit(1)
    cfg = Config.from_env()
    results = search(" ".join(sys.argv[1:]), chroma_dir=cfg.chroma_dir)
    for i, r in enumerate(results, 1):
        print(f"[{i}] ({r['source_type']}) {r['title']} · dist={r['distance']:.3f}")
        print(f"    {r['text'][:120]}...")
        print(f"    출처: {r['url']}\n")


if __name__ == "__main__":
    main()
