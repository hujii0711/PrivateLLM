"""bge-m3 임베딩 래퍼. encode_fn 주입으로 테스트 가능."""
from typing import Callable, Optional

MODEL_NAME = "BAAI/bge-m3"


class Embedder:
    def __init__(self, encode_fn: Optional[Callable[[list[str]], list]] = None,
                 model_name: str = MODEL_NAME):
        self._encode_fn = encode_fn
        self._model_name = model_name
        self._model = None

    def _lazy_encode(self, texts: list[str]) -> list:
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            import torch

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self._model = SentenceTransformer(self._model_name, device=device)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed(self, texts: list[str]) -> list:
        if not texts:
            return []
        fn = self._encode_fn or self._lazy_encode
        return fn(texts)
