"""청크 jsonl → Chroma 색인. 임베딩은 직접 계산해 전달."""
import json
from pathlib import Path

import chromadb

from .embedder import Embedder

COLLECTION = "jeonse_deposit"
_BATCH = 64


def build_index(*, chunks_path: Path, chroma_dir: Path, encode_fn=None) -> int:
    chunks = [json.loads(ln) for ln in Path(chunks_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not chunks:
        return 0

    embedder = Embedder(encode_fn=encode_fn)
    chroma_dir = Path(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    for i in range(0, len(chunks), _BATCH):
        batch = chunks[i:i + _BATCH]
        embeddings = embedder.embed([c["text"] for c in batch])
        col.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=embeddings,
            metadatas=[{k: c[k] for k in ("source_type", "title", "ref", "url", "date")}
                       for c in batch],
        )
    return len(chunks)


def main() -> None:
    from ..config import Config

    cfg = Config.from_env()
    cfg.ensure_dirs()
    n = build_index(chunks_path=cfg.chunks_dir / "chunks.jsonl", chroma_dir=cfg.chroma_dir)
    print(f"색인 {n}개 청크 → {cfg.chroma_dir} (collection={COLLECTION})")


if __name__ == "__main__":
    main()
