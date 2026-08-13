"""
embedder.py — 텍스트를 벡터(숫자 배열)로 변환하는 임베더 모듈

【임베딩(Embedding) 이란?】
텍스트를 고차원 숫자 벡터로 변환하는 기술입니다.
의미가 비슷한 문장은 벡터 공간에서 가까이 위치합니다.

    "보증금을 돌려받고 싶다"  → [0.12, -0.34, 0.89, ...]  (1024개 숫자)
    "임차인 보증금 반환 요청"  → [0.11, -0.32, 0.88, ...]  (비슷한 방향)
    "오늘 날씨가 맑다"        → [-0.45, 0.21, -0.03, ...]  (전혀 다른 방향)

이를 이용해 "의미적으로 유사한 문서"를 수학적으로 찾을 수 있습니다.

【bge-m3 모델 선택 이유】
BAAI/bge-m3 는 한국어·영어 등 다국어를 동시에 지원하는 임베딩 모델로,
1024차원 벡터를 생성합니다. 법률 문서처럼 한국어 중심 텍스트에 적합합니다.

【설계 포인트: encode_fn 주입(Dependency Injection)】
실제 모델 대신 가짜 인코더 함수를 주입할 수 있어 테스트가 쉽습니다.
    실제: QueryEmbedder()               → SentenceTransformer 사용
    테스트: QueryEmbedder(encode_fn=mock_fn) → 목(mock) 함수 사용
"""

from collections.abc import Callable  # 함수 타입 힌트에 사용 (Callable)

from .config import MODEL_NAME  # 기본 임베딩 모델 이름 상수


class QueryEmbedder:
    """사용자 질문을 벡터로 변환하는 클래스.

    SentenceTransformer(bge-m3) 를 사용해 질문 텍스트를 1024차원 벡터로 변환합니다.
    이 벡터를 ChromaDB 에 전달해 의미적으로 유사한 문서를 검색합니다.

    【지연 로딩(Lazy Loading) 패턴】
    SentenceTransformer 모델은 수백 MB 이상의 파일을 메모리에 올리는 무거운 작업입니다.
    __init__ 에서 바로 로드하지 않고, 첫 embed_query() 호출 시(_lazy) 로드합니다.
    이렇게 하면:
      - 서버 시작 속도가 빨라집니다.
      - 모델이 실제로 필요할 때까지 메모리를 아낄 수 있습니다.
    """

    def __init__(
        self,
        # Callable[[list[str]], list] : 문자열 리스트를 받아 리스트를 반환하는 함수 타입
        # | None                      : None 도 허용 (기본값이 None 이므로)
        encode_fn: Callable[[list[str]], list] | None = None,
        model_name: str = MODEL_NAME,
    ):
        """
        Args:
            encode_fn  : 텍스트 → 벡터 변환 함수. None 이면 SentenceTransformer 사용.
                         테스트 시 임의의 함수를 주입해 모델 로딩 없이 테스트 가능합니다.
            model_name : 사용할 SentenceTransformer 모델 이름 (Hugging Face 경로)
        """
        self._encode_fn = encode_fn   # 주입된 인코더 함수 (None 이면 실제 모델 사용)
        self._model_name = model_name  # 모델 이름 저장
        self._model = None             # 모델은 아직 로드하지 않음 (지연 로딩)

    def _lazy(self, texts: list[str]) -> list:
        """SentenceTransformer 모델을 처음 필요한 시점에 로드하고 인코딩합니다.

        "lazy" = 게으른, 즉 필요할 때까지 미룬다는 의미입니다.

        Args:
            texts: 임베딩할 텍스트 문자열 목록

        Returns:
            각 텍스트에 대한 1024차원 벡터를 담은 리스트 (list of list[float])
        """
        if self._model is None:
            # 모델이 아직 로드되지 않았으면 지금 로드합니다.
            import torch  # GPU/MPS 장치 감지에 사용
            from sentence_transformers import SentenceTransformer

            # Apple Silicon(M1/M2/M3) 에서는 MPS(Metal Performance Shaders) 가속을 사용합니다.
            # MPS 를 지원하지 않는 환경(Intel Mac, Linux)에서는 CPU 로 폴백합니다.
            device = "mps" if torch.backends.mps.is_available() else "cpu"

            # 모델을 지정한 장치에 로드합니다.
            self._model = SentenceTransformer(self._model_name, device=device)

        # normalize_embeddings=True : 벡터의 크기(norm)를 1로 정규화합니다.
        # 정규화된 벡터끼리의 내적(dot product)이 곧 코사인 유사도가 됩니다.
        # ChromaDB 가 코사인 거리를 사용하므로 반드시 정규화해야 합니다.
        vecs = self._model.encode(texts, normalize_embeddings=True)

        # numpy 배열을 파이썬 기본 list 로 변환합니다.
        # ChromaDB 는 파이썬 list 형식을 요구합니다.
        return [v.tolist() for v in vecs]

    def embed_query(self, query: str) -> list:
        """단일 질문 문자열을 벡터로 변환합니다.

        내부적으로 encode_fn 또는 _lazy 를 호출합니다.

        Args:
            query: 임베딩할 질문 텍스트 (예: "보증금 반환 소송 절차가 어떻게 되나요?")

        Returns:
            질문을 나타내는 1024차원 float 벡터 (list[float])
        """
        # 주입된 함수가 있으면 그것을, 없으면 _lazy(실제 모델)를 사용합니다.
        # `or` 연산자: 왼쪽이 falsy(None, 0, "" 등)이면 오른쪽을 사용합니다.
        fn = self._encode_fn or self._lazy

        # fn([query]) : 리스트로 감싸서 호출 (배치 처리 API)
        # [0]         : 결과 리스트의 첫 번째(유일한) 벡터를 꺼냄
        return fn([query])[0]
