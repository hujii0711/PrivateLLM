"""대상 법령·판례를 수집해 data/raw/{law,prec}/*.json 으로 저장한다."""
import json
import re
from pathlib import Path

from lxml import etree

from ..config import Config
from .law_client import LawClient
from .law_parser import parse_law
from .prec_parser import parse_prec

LAW_QUERIES = ["주택임대차보호법", "민법"]
PREC_QUERIES = ["임대차 보증금 반환", "임차보증금 반환", "보증금 반환 동시이행"]

_LAW_URL = "https://www.law.go.kr/법령/{name}"
_PREC_URL = "https://www.law.go.kr/판례/{id}"


def collect(*, client, out_dir: Path, law_queries=None, prec_queries=None) -> None:
    out_dir = Path(out_dir)
    (out_dir / "law").mkdir(parents=True, exist_ok=True)
    (out_dir / "prec").mkdir(parents=True, exist_ok=True)

    for q in (law_queries or LAW_QUERIES):
        # 검색은 가나다순 등으로 정렬되어 첫 결과가 질의어와 다를 수 있다
        # (예: "민법" 검색 시 "난민법"이 먼저 나옴). 법령명이 질의어와
        # 정확히 일치하는 결과를 골라 엉뚱한 법령 수집을 방지한다.
        search_xml = client.search(target="law", query=q, display=20)
        mst = _match_law_mst(search_xml, q)
        if not mst:
            continue
        law = parse_law(client.fetch(target="law", id=mst))
        if not law["articles"]:
            continue
        law["source_url"] = _LAW_URL.format(name=law["law_name"])
        _write(out_dir / "law" / f"{_slug(law['law_name'])}.json", law)

    seen: set[str] = set()
    for q in (prec_queries or PREC_QUERIES):
        search_xml = client.search(target="prec", query=q, display=20)
        for pid in _all(search_xml, "판례일련번호"):
            if pid in seen:
                continue
            seen.add(pid)
            body_xml = client.fetch(target="prec", id=pid)
            if "<PrecService" not in body_xml:
                continue   # 본문이 없는 검색 결과는 건너뛴다
            prec = parse_prec(body_xml)
            if not prec["case_no"]:
                continue
            prec["prec_id"] = pid
            prec["source_url"] = _PREC_URL.format(id=pid)
            _write(out_dir / "prec" / f"{pid}.json", prec)


def _match_law_mst(search_xml: str, query: str) -> str | None:
    """검색 결과 중 법령명이 질의어와 정확히 일치하는 법령일련번호를 고른다.

    실 API는 결과를 가나다순 등으로 정렬하므로 첫 결과가 질의어와 다를 수
    있다(예: "민법" 검색 시 "난민법"이 먼저). 정확히 일치하는 항목을 우선하고,
    없으면 첫 결과로 폴백한다. fixture는 단일 결과라 폴백 경로로 동작한다.
    """
    root = etree.fromstring(search_xml.encode("utf-8"))
    first_mst = None
    want = query.strip()
    # 결과 행 단위로 (법령명한글, 법령일련번호) 쌍을 본다. law 검색 결과 루트
    # 바로 아래에 행 요소들이 있고, 각 행에 두 태그가 함께 들어 있다.
    for row in root.iter():
        name_el = row.find("법령명한글")
        mst_el = row.find("법령일련번호")
        if mst_el is None or not (mst_el.text and mst_el.text.strip()):
            continue
        mst = mst_el.text.strip()
        if first_mst is None:
            first_mst = mst
        name = (name_el.text or "").strip() if name_el is not None else ""
        if name == want:
            return mst
    return first_mst


def _write(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _all(xml_text: str, tag: str) -> list[str]:
    root = etree.fromstring(xml_text.encode("utf-8"))
    return [e.text.strip() for e in root.iter(tag) if e.text and e.text.strip()]


def _slug(s: str) -> str:
    return re.sub(r"\s+", "_", s.strip())


def main() -> None:
    cfg = Config.from_env()
    cfg.ensure_dirs()
    collect(client=LawClient(oc=cfg.oc), out_dir=cfg.raw_dir)
    print(f"수집 완료 → {cfg.raw_dir}")


if __name__ == "__main__":
    main()
