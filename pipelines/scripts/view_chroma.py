"""ChromaDB에 저장된 청크 데이터를 터미널에서 조회하는 스크립트.

사용법:
    # 전체 목록 (기본 20개)
    python scripts/view_chroma.py

    # 개수 지정
    python scripts/view_chroma.py --limit 50

    # 법령만 필터
    python scripts/view_chroma.py --source 법령

    # 판례만 필터
    python scripts/view_chroma.py --source 판례

    # 키워드로 유사도 검색
    python scripts/view_chroma.py --query "보증금 반환"

    # 컬렉션 통계만 확인
    python scripts/view_chroma.py --stats
"""

import argparse
import sys
from pathlib import Path

# pipelines 패키지 경로 추가
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipelines" / "src"))

import chromadb

CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "jeonse_deposit"

# ANSI 색상 코드
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION)


def show_stats(col):
    total = col.count()
    print(f"\n{BOLD}📦 컬렉션: {COLLECTION}{RESET}")
    print(f"   총 청크 수: {CYAN}{total}{RESET}개")

    # source_type별 집계
    result = col.get(include=["metadatas"])
    source_counts: dict[str, int] = {}
    for m in result["metadatas"]:
        src = m.get("source_type", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    print(f"\n{BOLD}📊 source_type별 분포:{RESET}")
    for src, cnt in sorted(source_counts.items()):
        bar = "█" * (cnt // max(1, total // 30))
        print(f"   {GREEN}{src:8}{RESET} {bar} {cnt}개")
    print()


def show_list(col, limit: int, source_filter: str | None):
    where = {"source_type": source_filter} if source_filter else None
    result = col.get(
        where=where,
        limit=limit,
        include=["metadatas", "documents"],
    )

    ids       = result["ids"]
    docs      = result["documents"]
    metadatas = result["metadatas"]

    print(f"\n{BOLD}🔍 조회 결과 ({len(ids)}개){RESET}\n")
    for i, (rid, doc, meta) in enumerate(zip(ids, docs, metadatas), 1):
        print(f"{CYAN}[{i:03d}]{RESET} {BOLD}{meta.get('title', '')}{RESET}")
        print(f"       ID          : {DIM}{rid}{RESET}")
        print(f"       source_type : {GREEN}{meta.get('source_type', '')}{RESET}")
        print(f"       ref         : {meta.get('ref', '')}")
        print(f"       date        : {meta.get('date', '')}")
        print(f"       url         : {DIM}{meta.get('url', '')}{RESET}")
        # 본문 미리보기 (80자 이내)
        preview = doc[:120].replace("\n", " ")
        if len(doc) > 120:
            preview += "…"
        print(f"       text        : {YELLOW}{preview}{RESET}")
        print()


def show_query(col, query: str, n_results: int = 5):
    from pipelines.index.embedder import Embedder
    embedder = Embedder()
    vec = embedder.embed([query])[0]

    result = col.query(
        query_embeddings=[vec],
        n_results=n_results,
        include=["metadatas", "documents", "distances"],
    )

    ids        = result["ids"][0]
    docs       = result["documents"][0]
    metadatas  = result["metadatas"][0]
    distances  = result["distances"][0]

    print(f"\n{BOLD}🔎 유사도 검색: \"{query}\" (상위 {n_results}개){RESET}\n")
    for i, (rid, doc, meta, dist) in enumerate(zip(ids, docs, metadatas, distances), 1):
        score = 1 - dist  # cosine distance → similarity
        bar = "█" * int(score * 20)
        print(f"{CYAN}[{i}]{RESET} {BOLD}{meta.get('title', '')}{RESET}")
        print(f"     유사도 : {GREEN}{score:.4f}{RESET} {bar}")
        print(f"     source : {meta.get('source_type', '')} / {meta.get('ref', '')}")
        preview = doc[:120].replace("\n", " ")
        if len(doc) > 120:
            preview += "…"
        print(f"     text   : {YELLOW}{preview}{RESET}")
        print()


def main():
    parser = argparse.ArgumentParser(description="ChromaDB 데이터 조회 도구")
    parser.add_argument("--limit",  type=int, default=20, help="조회 개수 (기본 20)")
    parser.add_argument("--source", choices=["법령", "판례", "해설", "상담사례"], help="source_type 필터")
    parser.add_argument("--query",  type=str, help="유사도 검색 키워드")
    parser.add_argument("--stats",  action="store_true", help="통계만 출력")
    args = parser.parse_args()

    col = get_collection()
    show_stats(col)

    if args.stats:
        return

    if args.query:
        show_query(col, args.query, n_results=args.limit)
    else:
        show_list(col, limit=args.limit, source_filter=args.source)


if __name__ == "__main__":
    main()
