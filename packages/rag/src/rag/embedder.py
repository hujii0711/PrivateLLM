"""질의 임베더 — Plan 1과 동일한 bge-m3(1024-dim). encode_fn 주입으로 테스트 가능."""
from typing import Callable, Optional

from .config import MODEL_NAME


class QueryEmbedder:
    def __init__(self, encode_fn: Optional[Callable[[list[str]], list]] = None,
                 model_name: str = MODEL_NAME):
        self._encode_fn = encode_fn
        self._model_name = model_name
        self._model = None

    def _lazy(self, texts: list[str]) -> list:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import torch

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self._model = SentenceTransformer(self._model_name, device=device)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed_query(self, query: str) -> list:
        fn = self._encode_fn or self._lazy
        return fn([query])[0]
