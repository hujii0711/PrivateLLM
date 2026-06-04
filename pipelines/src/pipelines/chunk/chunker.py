"""법령·판례 JSON → Chunk(jsonl). 구조 인지 청킹."""
import json
from pathlib import Path

from ..clean.normalize import normalize_text
from ..schema import Chunk, make_chunk


def chunk_law(law: dict, *, date: str) -> list[Chunk]:
    name = law["law_name"]
    url = law.get("source_url", "")
    chunks: list[Chunk] = []
    for art in law["articles"]:
        no = art["article_no"]
        title = art.get("title", "")
        head = f"{name} {no}" + (f"({title})" if title else "")
        chunks.append(make_chunk(
            id=f"law-{name}-{no}",
            text=normalize_text(art["text"]),
            source_type="법령",
            title=head,
            ref=no,
            url=url,
            date=date,
        ))
    return chunks


def chunk_prec(prec: dict) -> list[Chunk]:
    title = f"{prec['court']} {prec['case_no']} {prec.get('case_name', '')}".strip()
    date = _fmt_date(prec.get("decided_on", ""))
    url = prec.get("source_url", "")
    pid = prec.get("prec_id", prec.get("case_no", ""))

    chunks: list[Chunk] = []
    for ref, key in (("판시사항", "holding_summary"), ("판결요지", "judgment_summary")):
        text = normalize_text(prec.get(key, ""))
        if not text:
            continue
        chunks.append(make_chunk(
            id=f"prec-{pid}-{ref}",
            text=text,
            source_type="판례",
            title=title,
            ref=ref,
            url=url,
            date=date,
        ))
    return chunks


def _fmt_date(yyyymmdd: str) -> str:
    s = yyyymmdd.strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def build_all(raw_dir: Path, out_path: Path, *, law_date: str = "") -> int:
    """raw_dir의 모든 JSON → out_path(jsonl). 작성된 청크 수 반환."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for p in sorted((raw_dir / "law").glob("*.json")):
            law = json.loads(p.read_text(encoding="utf-8"))
            for c in chunk_law(law, date=law_date):
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
        for p in sorted((raw_dir / "prec").glob("*.json")):
            prec = json.loads(p.read_text(encoding="utf-8"))
            for c in chunk_prec(prec):
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
    return n


def main() -> None:
    from ..config import Config

    cfg = Config.from_env()
    cfg.ensure_dirs()
    out = cfg.chunks_dir / "chunks.jsonl"
    n = build_all(cfg.raw_dir, out)
    print(f"청크 {n}개 → {out}")


if __name__ == "__main__":
    main()
