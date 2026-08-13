"""법령·판례 JSON → Chunk(jsonl). 구조 인지 청킹."""

import json
from pathlib import Path

from ..clean.normalize import normalize_text
from ..schema import Chunk, make_chunk


def chunk_law(law: dict, *, date: str) -> list[Chunk]:
    """법령 1건을 조문 단위 Chunk 목록으로 변환한다.

    법령은 조문 하나가 검색과 인용의 자연스러운 최소 단위이므로, 각 조문을
    독립된 Chunk로 만든다. 법령명, 조문번호, 조문제목은 title/ref 메타데이터에
    보존해 검색 결과에서 근거 조문을 바로 표시할 수 있게 한다.
    """

    name = law["law_name"]
    url = law.get("source_url", "") # 키값 없으면 기본값 공백
    # 타입 힌팅(Type Hinting, 타입 어노테이션) 문법
    # chunks: 내가 지금 만들 변수의 이름이야.
    # : list[Chunk]: 이 변수에는 Chunk라는 클래스(객체)들만 요소로 들어가는 리스트(list)가 담길 예정이야. (타입 힌트)
    # = []: 일단 지금은 비어있는 리스트로 초기화해 둘게.
    chunks: list[Chunk] = []
    for art in law["articles"]:
        no = art["article_no"]
        title = art.get("title", "")
        # 조문 제목은 검색 결과에서 법령명 + 조문번호 + 조문명을 한 번에 보이게 만든다.
        head = f"{name} {no}" + (f"({title})" if title else "")
        chunks.append(
            make_chunk(
                id=f"law-{name}-{no}",
                text=normalize_text(art["text"]),
                source_type="법령",
                title=head,
                ref=no,
                url=url,
                date=date,
            )
        )
    return chunks


def chunk_prec(prec: dict) -> list[Chunk]:
    """판례 1건을 주요 요약 섹션별 Chunk 목록으로 변환한다.

    판례 전문은 길고 잡음이 많을 수 있어, 우선 답변 근거로 쓰기 좋은 판시사항과
    판결요지를 각각 별도 Chunk로 만든다. 비어 있는 섹션은 색인 품질을 위해
    저장하지 않는다.
    """

    title = f"{prec['court']} {prec['case_no']} {prec.get('case_name', '')}".strip()
    date = _fmt_date(prec.get("decided_on", ""))
    url = prec.get("source_url", "")
    pid = prec.get("prec_id", prec.get("case_no", ""))

    chunks: list[Chunk] = []
    for ref, key in (("판시사항", "holding_summary"), ("판결요지", "judgment_summary")):
        text = normalize_text(prec.get(key, ""))
        if not text:
            continue
        # 판례는 본문 전체보다 검색에 유리한 핵심 요약만 섹션별로 따로 저장한다.
        chunks.append(
            make_chunk(
                id=f"prec-{pid}-{ref}",
                text=text,
                source_type="판례",
                title=title,
                ref=ref,
                url=url,
                date=date,
            )
        )
    return chunks


def _fmt_date(yyyymmdd: str) -> str:
    """YYYYMMDD 형식 날짜를 YYYY-MM-DD로 정규화한다.

    API 원본 값이 이미 다른 형식이거나 비어 있으면 원문을 그대로 돌려보내
    호출자가 날짜 누락과 비표준 값을 구분할 수 있게 한다.
    """

    s = yyyymmdd.strip()  # 모든 공백(스페이스, 탭\t, 줄바꿈\n)을 제거
    if len(s) == 8 and s.isdigit():  # 이 문자열이 오직 숫자로만 이루어져 있는가를 판별
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s

# raw_dir: Path타입 힌트 — Path 객체를 받겠다는 명시
# * 이 뒤의 인자는 반드시 키워드로만 호출 가능
def build_all(raw_dir: Path, out_path: Path, *, law_date: str = "") -> int:
    """raw_dir의 모든 JSON을 읽어 하나의 청크 jsonl 파일로 만든다.

    `raw/law/*.json`은 `chunk_law`, `raw/prec/*.json`은 `chunk_prec`로 변환한다.
    반환값은 실제로 파일에 쓴 청크 수라서 CLI 출력과 테스트 검증에 쓸 수 있다.
    """

    # .parent — 파일의 상위 폴더 경로
    # parents=True — 중간 폴더도 자동 생성
    # exist_ok=True — 이미 있어도 오류 없이 통과
    # out_path = "data/chunks/result.jsonl" 이면
    # out_path.parent = "data/chunks/" 폴더를 생성
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    # "w" — 쓰기 모드 (파일이 없으면 생성, 있으면 덮어쓰기)
    # encoding="utf-8" — 한글 깨짐 방지
    # with 블록이 끝나면 자동으로 파일을 닫아줌 (f.close() 불필요)
    with out_path.open("w", encoding="utf-8") as f:
        # 법령 JSON은 조문별로, 판례 JSON은 요약 섹션별로 순서대로 합쳐 하나의 jsonl로 만든다.
        # .glob("*.json")해당 폴더의 모든 .json 파일 찾기
        # sorted(...)파일명 알파벳 순으로 정렬
        for p in sorted((raw_dir / "law").glob("*.json")):
            # p.read_text() — 파일 전체를 문자열로 읽기
            # json.loads() — JSON 문자열 → 파이썬 딕셔너리로 변환
            law = json.loads(p.read_text(encoding="utf-8"))
            for c in chunk_law(law, date=law_date):
                # chunk_law(law, ...) — law 딕셔너리를 청크 단위로 쪼개는 함수
                # json.dumps(c, ensure_ascii=False) — 딕셔너리 → JSON 문자열 변환
                # ensure_ascii=False — 한글을 \uXXXX 대신 그대로 저장
                # + "\n" — JSONL 형식은 한 줄에 JSON 하나씩
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
        for p in sorted((raw_dir / "prec").glob("*.json")):
            prec = json.loads(p.read_text(encoding="utf-8"))
            for c in chunk_prec(prec):
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
                # raw/law/*.json  →  chunk_law()  →  한 줄씩 jsonl에 저장
                # raw/prec/*.json →  chunk_prec() →  한 줄씩 jsonl에 저장
                #                                          ↓
                #                                     총 청크 수 반환 (n)
    return n


def main() -> None:
    """환경 설정을 읽고 청킹 산출물을 기본 위치에 생성한다."""
    from ..config import Config

    cfg = Config.from_env()
    cfg.ensure_dirs()
    out = cfg.chunks_dir / "chunks.jsonl"
    n = build_all(cfg.raw_dir, out)
    print(f"청크 {n}개 → {out}")


if __name__ == "__main__":
    main()
