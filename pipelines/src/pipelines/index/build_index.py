"""청크 jsonl → Chroma 색인. 임베딩은 직접 계산해 전달."""

import json
from pathlib import Path

import chromadb

from .embedder import Embedder

COLLECTION = "jeonse_deposit"
_BATCH = 64


# chunks_path: Path / jsonl 파일 경로
# chroma_dir: Path / Chroma DB 저장 폴더
# encode_fn=None / 인코딩 함수 (선택, 기본값 None)
def build_index(*, chunks_path: Path, chroma_dir: Path, encode_fn=None) -> int:
    """청크 jsonl 파일을 읽어 Chroma 컬렉션에 업서트한다.

    각 줄의 Chunk를 문서 본문, 임베딩, 메타데이터로 나눠 저장한다. 이미 같은 id가
    있으면 Chroma의 upsert 동작으로 갱신되므로, 청킹 결과를 다시 만들어도 색인을
    같은 함수로 재생성할 수 있다.
    """
    # Path()는 문자열이든 Path 객체든 상관없이 항상 Path 객체로 변환해 줍니다.
    # 함수 시그니처에 : Path 타입 힌트가 있어도, 파이썬은 타입을 강제하지 않습니다. 그래서 방어적으로 Path()로 한 번 더 감쌉니다.
    # 외부에서 문자열로 들어와도 Path 객체로 통일해서, 이후 코드에서 Path의 편리한 기능을 안전하게 쓰기 위한 방어적 변환입니다.

    # 문자열로 넘어온 경우
    # chroma_dir = "data/chroma"
    # chroma_dir = Path(chroma_dir)

    # # 이제 Path 메서드 사용 가능
    # chroma_dir.mkdir(parents=True, exist_ok=True)  # ✅
    # client = chromadb.PersistentClient(path=str(chroma_dir))  # str()로 다시 문자열 변환

    # 1. 파일 전체를 문자열로 읽기
    # text = Path(chunks_path).read_text(encoding="utf-8")

    # 2. 줄 단위로 분리
    # lines = text.splitlines()

    # 3. 빈 줄 제거 (if ln.strip())
    # 4. 각 줄을 JSON → 딕셔너리로 변환
    # chunks = [json.loads(ln) for ln in lines if ln.strip()]
    chunks = [json.loads(ln) for ln in Path(chunks_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    # 결과 포맷은 아래와 같다
    # chunks = [
    #     {"id": 1, "text": "hello"},
    #     {"id": 2, "text": "world"},
    #     {"id": 3, "text": "foo"}
    # ]
    if not chunks:
        return 0

    # Embedder(encode_fn=encode_fn) / 임베딩 객체 생성Path(chroma_dir)
    # 문자열이어도 Path로 변환 / mkdir(parents=True, exist_ok=True)
    # 폴더 자동 생성 / PersistentClient / 디스크에 저장되는 Chroma 클라이언트
    # get_or_create_collection / 컬렉션이 없으면 생성, 있으면 가져옴
    # "hnsw:space": "cosine" / 벡터 유사도 계산 방식을 코사인으로 설정
    embedder = Embedder(encode_fn=encode_fn)
    chroma_dir = Path(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(chroma_dir))  # 문자열로 형변환
    col = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    # _BATCH 가 100이라면, 100개씩 잘라서 처리
    # range(0, len(chunks), _BATCH) — 0, 100, 200, 300... 순서로 이동

    # python# 예: chunks가 250개, _BATCH=100 이면
    # i=0   → batch = chunks[0:100]    # 100개
    # i=100 → batch = chunks[100:200]  # 100개
    # i=200 → batch = chunks[200:250]  # 50개
    for i in range(0, len(chunks), _BATCH):
        batch = chunks[i : i + _BATCH]
        # 임베딩 모델 호출 비용을 줄이고 메모리 사용량을 제한하기 위해 배치 단위로 처리한다.
        # [c["text"] for c in batch] — batch의 각 청크에서 "text" 값만 추출
        # embedder.embed(...) — 텍스트 리스트를 벡터로 변환
        # 예시
        # ["민법 제1조...", "형법 제2조..."]  →  [[0.12, 0.34, ...], [0.56, 0.78, ...]]
        embeddings = embedder.embed([c["text"] for c in batch])

        # upsert — 있으면 갱신, 없으면 삽입 (update + insert 합성어)
        col.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=embeddings,
            metadatas=[{k: c[k] for k in ("source_type", "title", "ref", "url", "date")} for c in batch],
        )
        # metadatas 부분 분해:
        # 딕셔너리 컴프리헨션
        # {k: c[k] for k in ("source_type", "title", "ref", "url", "date")}

        # 풀어쓰면
        # {
        #     "source_type": c["source_type"],
        #     "title":       c["title"],
        #     "ref":         c["ref"],
        #     "url":         c["url"],
        #     "date":        c["date"],
        # }
    return len(chunks)

    # 전체 흐름 요약
    # jsonl 파일 읽기 → 딕셔너리 리스트로 변환
    #         ↓
    # 청크가 없으면 0 반환
    #         ↓
    # Chroma DB 클라이언트 & 컬렉션 준비
    #         ↓
    # _BATCH 단위로 반복
    #     ├─ 텍스트 추출 → 임베딩 벡터 생성
    #     └─ id / 문서 / 벡터 / 메타데이터 → Chroma에 upsert
    #         ↓
    # 총 청크 수 반환


def main() -> None:
    """환경 설정을 읽고 기본 청크 파일을 Chroma 색인으로 만든다."""

    from ..config import Config

    cfg = Config.from_env()
    cfg.ensure_dirs()
    n = build_index(chunks_path=cfg.chunks_dir / "chunks.jsonl", chroma_dir=cfg.chroma_dir)
    print(f"색인 {n}개 청크 → {cfg.chroma_dir} (collection={COLLECTION})")


if __name__ == "__main__":
    main()
