"""
retriever.py — ChromaDB 벡터 검색 및 근거 품질 판정 모듈

【이 파일이 하는 일】
1. 사용자 질문을 벡터로 변환합니다. (embedder 위임)
2. ChromaDB 에서 코사인 유사도가 높은 문서를 top-k 개 검색합니다.
3. 검색된 문서가 답변에 쓸 수 있는 충분한 근거인지 판정합니다. (is_grounded)

【ChromaDB 란?】
벡터(숫자 배열)를 저장하고 유사도 기반 검색을 수행하는 오픈소스 벡터 데이터베이스입니다.
일반 DB(MySQL, PostgreSQL)가 텍스트 일치를 찾는다면,
ChromaDB 는 "의미적으로 비슷한" 문서를 찾습니다.

【코사인 유사도 vs 코사인 거리】
ChromaDB 는 내부적으로 "코사인 거리(distance)"를 저장합니다.
  distance = 1 - cosine_similarity
  similarity = 1 - distance  ← 이 파일에서 변환

따라서 distance=0 이면 완전히 같은 방향(유사도 1.0),
distance=1 이면 직교(유사도 0.0), distance=2 이면 반대 방향(유사도 -1.0) 입니다.
"""

import chromadb  # ChromaDB 클라이언트 라이브러리

from .config import RagConfig  # RAG 설정 (경로, 컬렉션, top_k 등)
from .embedder import QueryEmbedder  # 텍스트 → 벡터 변환기
from .types import Retrieved  # 검색 결과 데이터 타입


class Retriever:
    """ChromaDB 에서 법령·판례를 검색하고 근거 충분성을 판정하는 클래스.

    사용 예:
        cfg = RagConfig.from_env()
        retriever = Retriever(cfg)
        hits = retriever.retrieve("보증금 반환 소송 절차")
        if retriever.is_grounded(hits):
            # 근거가 충분하면 LLM에게 전달
            ...
    """

    def __init__(self, config: RagConfig, encode_fn=None):
        """Retriever 를 초기화하고 ChromaDB 컬렉션에 연결합니다.

        Args:
            config    : RAG 동작 설정 (chroma_dir, collection, top_k 등)
            encode_fn : 테스트용 가짜 인코더 함수. None 이면 실제 모델 사용.
        """
        self._cfg = config

        # QueryEmbedder : 질문 텍스트 → 1024차원 벡터 변환 담당
        self._embedder = QueryEmbedder(
            encode_fn=encode_fn,
            model_name=config.model_name,
        )

        # PersistentClient : 디스크에 저장된 ChromaDB 파일을 열어 연결합니다.
        # path 는 색인 시 사용한 디렉터리와 동일해야 합니다.
        client = chromadb.PersistentClient(path=str(config.chroma_dir))

        # get_collection : 이미 존재하는 컬렉션(테이블)을 가져옵니다.
        # 컬렉션이 없으면 예외가 발생합니다. (색인이 먼저 실행되어야 합니다)
        self._col = client.get_collection(config.collection)

    def retrieve(self, query: str) -> list[Retrieved]:
        """질문과 의미적으로 유사한 법령·판례 문서를 top-k 개 검색합니다.

        처리 흐름:
          1. 질문 텍스트 → 1024차원 벡터 변환
          2. ChromaDB 에 벡터 유사도 검색 요청
          3. 결과를 Retrieved 객체 리스트로 변환하여 반환

        Args:
            query: 사용자가 입력한 질문 텍스트

        Returns:
            유사도 높은 순서로 정렬된 Retrieved 객체 리스트 (최대 top_k 개)
        """
        # Step 1: 질문을 벡터로 변환
        qvec = self._embedder.embed_query(query)

        # Step 2: ChromaDB 쿼리 실행
        # query_embeddings : 검색에 사용할 벡터 (리스트로 감싸야 함)
        # n_results         : 반환할 최대 결과 수
        # include           : 반환받을 데이터 종류 (본문, 메타데이터, 거리)
        res = self._col.query(
            query_embeddings=[qvec],
            n_results=self._cfg.top_k,
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB 응답 구조:
        # res = {
        #   "ids":       [["id1", "id2", ...]],   ← 2중 리스트 (배치 처리용)
        #   "documents": [["본문1", "본문2", ...]],
        #   "metadatas": [[{"title": ..., "url": ...}, ...]],
        #   "distances": [[0.12, 0.25, ...]],
        # }
        # [0] 인덱스 : 첫 번째 쿼리 결과 (우리는 쿼리를 1개만 보냄)

        # .get() 으로 안전하게 값을 가져옵니다 (키가 없으면 None 반환)
        res_ids = res.get("ids")
        ids = res_ids[0] if res_ids is not None else []

        res_docs = res.get("documents")
        docs = res_docs[0] if res_docs is not None else []

        res_metas = res.get("metadatas")
        metas = res_metas[0] if res_metas is not None else []

        res_dists = res.get("distances")
        dists = res_dists[0] if res_dists is not None else []

        # Step 3: 결과를 Retrieved 객체 리스트로 변환
        out: list[Retrieved] = []
        for i, id_ in enumerate(ids):
            # 각 필드를 안전하게 추출 (인덱스 범위 초과 방지)
            doc = docs[i] if i < len(docs) else ""
            meta = metas[i] if i < len(metas) else {}
            meta = meta or {}  # None 이면 빈 딕셔너리로 대체

            dist = dists[i] if i < len(dists) else 0.0

            out.append(
                Retrieved(
                    id=id_,
                    text=doc,
                    # 코사인 거리 → 코사인 유사도로 변환 (1.0 - distance)
                    similarity=1.0 - float(dist),
                    # dict.get(key) : 키가 없으면 None 반환
                    # str(...) : None 이 오더라도 문자열로 안전하게 변환
                    # or ""    : None 인 경우 빈 문자열로 대체
                    source_type=str(meta.get("source_type") or ""),
                    title=str(meta.get("title") or ""),
                    ref=str(meta.get("ref") or ""),
                    url=str(meta.get("url") or ""),
                    date=str(meta.get("date") or ""),
                )
            )
        return out

    def is_grounded(self, hits: list[Retrieved]) -> bool:
        """검색 결과가 답변 생성에 충분한 근거인지 판정합니다.

        판정 기준:
          1. 검색 결과가 1건 이상 있어야 합니다.
          2. 가장 유사한 문서(hits[0])의 유사도가 min_similarity 이상이어야 합니다.
             (hits 는 유사도 내림차순으로 정렬되므로 [0]이 가장 유사합니다)

        False 를 반환하면 pipeline.py 에서 "관련 근거를 찾지 못했습니다" 메시지를 반환합니다.

        Args:
            hits: retrieve() 가 반환한 검색 결과 리스트

        Returns:
            True  : 근거 충분 → LLM 에게 답변 생성 요청
            False : 근거 부족 → 사전 정의된 거부 메시지 반환
        """
        # bool(hits)             : 리스트가 비어있지 않은지 확인
        # hits[0].similarity ... : 가장 유사한 문서의 유사도가 임계값 이상인지 확인
        return bool(hits) and hits[0].similarity >= self._cfg.min_similarity
