"""Chroma top-k 검색 → Retrieved 리스트 + grounding 판정."""
import chromadb

from .config import RagConfig
from .embedder import QueryEmbedder
from .types import Retrieved


class Retriever:
    def __init__(self, config: RagConfig, encode_fn=None):
        self._cfg = config
        self._embedder = QueryEmbedder(encode_fn=encode_fn,
                                       model_name=config.model_name)
        client = chromadb.PersistentClient(path=str(config.chroma_dir))
        self._col = client.get_collection(config.collection)

    def retrieve(self, query: str) -> list[Retrieved]:
        qvec = self._embedder.embed_query(query)
        res = self._col.query(
            query_embeddings=[qvec], n_results=self._cfg.top_k,
            include=["documents", "metadatas", "distances"],
        )
        out: list[Retrieved] = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0],
                                   res["distances"][0]):
            out.append(Retrieved(
                id="",
                text=doc,
                similarity=1.0 - float(dist),
                source_type=meta.get("source_type", ""),
                title=meta.get("title", ""),
                ref=meta.get("ref", ""),
                url=meta.get("url", ""),
                date=meta.get("date", ""),
            ))
        for r_, id_ in zip(out, res["ids"][0]):
            r_.id = id_
        return out

    def is_grounded(self, hits: list[Retrieved]) -> bool:
        return bool(hits) and hits[0].similarity >= self._cfg.min_similarity
