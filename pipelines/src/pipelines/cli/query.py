"""검색 스모크 CLI: 질의 → top-k 청크."""
import sys
from pathlib import Path

import chromadb

from ..index.build_index import COLLECTION
from ..index.embedder import Embedder


def search(query: str, *, chroma_dir: Path, encode_fn=None, k: int = 6) -> list[dict]:
    """질문 문자열을 임베딩해 Chroma에서 가까운 청크를 조회한다.

    반환값은 CLI 출력과 테스트에서 바로 쓰기 쉽도록 Chroma 응답의 id, 본문,
    거리값, 메타데이터를 평평한 dict 목록으로 합친 형태다.
    """

    embedder = Embedder(encode_fn=encode_fn)
    qvec = embedder.embed([query])[0]
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_collection(COLLECTION)
    res = col.query(query_embeddings=[qvec], n_results=k,
                    include=["documents", "metadatas", "distances"])
    res_ids = res.get("ids")
    ids = res_ids[0] if res_ids is not None else []
    res_docs = res.get("documents")
    docs = res_docs[0] if res_docs is not None else []
    res_metas = res.get("metadatas")
    metas = res_metas[0] if res_metas is not None else []
    res_dists = res.get("distances")
    dists = res_dists[0] if res_dists is not None else []

    out = []
    for i, id_ in enumerate(ids):
        doc = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        meta = meta or {}
        dist = dists[i] if i < len(dists) else 0.0
        out.append({"id": id_, "text": doc, "distance": dist, **meta})
    return out


def main() -> None:
    """명령행 인자를 질문으로 받아 top-k 검색 결과를 콘솔에 출력한다."""

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
