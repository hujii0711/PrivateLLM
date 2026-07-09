"""bge-m3 임베딩 래퍼. encode_fn 주입으로 테스트 가능."""

# Callable 이란?
# Callable은 함수, 메서드, 람다 등 호출 가능한(() 로 실행 가능한) 객체를 타입으로 표현합니다.
# "이 변수는 호출 가능한 함수여야 한다" 고 타입으로 명시할 때 사용합니다.
from collections.abc import Callable

MODEL_NAME = "BAAI/bge-m3"


class Embedder:
    """텍스트 목록을 검색용 임베딩 벡터로 변환하는 래퍼.

    기본 실행에서는 bge-m3 SentenceTransformer 모델을 지연 로딩하고, 테스트에서는
    `encode_fn`을 주입해 무거운 모델 다운로드나 추론 없이 같은 인터페이스를 검증한다.
    """
    # Callable이 없다면?
    # def run(func):         # func가 뭔지 전혀 알 수 없음 😕
    # Callable이 있다면?
    # def run(func: Callable[[str], int]):  # func는 str 받아 int 반환하는 함수 😊

    # Callable[[입력타입],  반환타입]
    # [list[str]]   list --> str 리스트를 받아서 → 리스트를 반환하는 함수 타입
    # | 는 유니온 타입 (Python 3.10+) Callable 또는 None 둘 다 허용
    def __init__(self, encode_fn: Callable[[list[str]], list] | None = None,
                 model_name: str = MODEL_NAME):
        """임베딩 함수 또는 모델명을 설정한다."""

        self._encode_fn = encode_fn
        self._model_name = model_name
        self._model = None

    def _lazy_encode(self, texts: list[str]) -> list:
        """필요한 순간에 SentenceTransformer 모델을 로드해 임베딩을 계산한다.

        macOS에서 MPS 사용이 가능하면 GPU 백엔드를 쓰고, 결과는 Chroma에 넘기기
        쉬운 일반 Python list 형태로 변환한다.
        """

        if self._model is None:
            import torch
            from sentence_transformers import SentenceTransformer

            device = "mps" if torch.backends.mps.is_available() else "cpu"
            self._model = SentenceTransformer(self._model_name, device=device)
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed(self, texts: list[str]) -> list:
        """텍스트 목록을 임베딩 벡터 목록으로 변환한다.

        빈 입력은 모델 로딩 없이 빈 목록을 반환하고, 주입된 `encode_fn`이 있으면
        그것을 우선 사용해 테스트와 운영 경로를 같은 메서드로 다룬다.
        """

        if not texts:
            return []
        fn = self._encode_fn or self._lazy_encode
        return fn(texts)
