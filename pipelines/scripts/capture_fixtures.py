"""실제 OPEN API를 호출해 파서 테스트용 fixture를 저장한다.

실행: cd pipelines && uv run python scripts/capture_fixtures.py
필요: pipelines/.env 의 LAW_API_OC
"""
from pathlib import Path

from pipelines.config import Config
from pipelines.ingest.law_client import LawClient

FIX = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def main() -> None:
    cfg = Config.from_env()
    client = LawClient(oc=cfg.oc)
    FIX.mkdir(parents=True, exist_ok=True)

    # 1) 법령 본문: 주택임대차보호법
    search = client.search(target="law", query="주택임대차보호법", display=1)
    (FIX / "law_search.xml").write_text(search, encoding="utf-8")
    mst = _first_tag(search, "법령일련번호") or _first_tag(search, "MST")
    if mst:
        law = client.fetch(target="law", id=mst)
        (FIX / "law_주택임대차보호법.xml").write_text(law, encoding="utf-8")

    # 2) 판례 검색 + 본문 1건
    #    검색 결과 중 일부(예: 국세법령정보시스템 출처)는 본문 XML이 제공되지 않고
    #    "일치하는 판례가 없습니다" 오류를 돌려준다. 실제 <PrecService> 본문을
    #    돌려주는 첫 판례를 골라 fixture 로 저장한다.
    prec_search = client.search(target="prec", query="임대차 보증금 반환", display=5)
    (FIX / "prec_search.xml").write_text(prec_search, encoding="utf-8")
    for pid in _all_tags(prec_search, "판례일련번호"):
        prec = client.fetch(target="prec", id=pid)
        if "<PrecService" in prec:
            (FIX / "prec_one.xml").write_text(prec, encoding="utf-8")
            break
    else:
        print("경고: 본문이 제공되는 판례를 찾지 못했습니다.")

    print("저장된 fixture:", sorted(p.name for p in FIX.glob("*.xml")))


def _first_tag(xml_text: str, tag: str) -> str | None:
    import lxml.etree as etree

    root = etree.fromstring(xml_text.encode("utf-8"))
    el = root.find(f".//{tag}")
    return el.text.strip() if el is not None and el.text else None


def _all_tags(xml_text: str, tag: str) -> list[str]:
    import lxml.etree as etree

    root = etree.fromstring(xml_text.encode("utf-8"))
    return [el.text.strip() for el in root.iter(tag) if el.text and el.text.strip()]


if __name__ == "__main__":
    main()
