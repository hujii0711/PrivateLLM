import json

from pipelines.ingest.fetch_corpus import collect


class StubClient:
    """fixture XML을 그대로 돌려주는 가짜 클라이언트."""
    def __init__(self, fixtures_dir):
        self.f = fixtures_dir

    def search(self, *, target, query, display=20):
        name = "law_search.xml" if target == "law" else "prec_search.xml"
        return (self.f / name).read_text(encoding="utf-8")

    def fetch(self, *, target, id):
        name = "law_주택임대차보호법.xml" if target == "law" else "prec_one.xml"
        return (self.f / name).read_text(encoding="utf-8")


def test_collect_writes_law_and_prec_json(tmp_path, fixtures_dir):
    client = StubClient(fixtures_dir)
    collect(client=client, out_dir=tmp_path,
            law_queries=["주택임대차보호법"],
            prec_queries=["임대차 보증금 반환"])

    laws = list((tmp_path / "law").glob("*.json"))
    precs = list((tmp_path / "prec").glob("*.json"))
    assert laws and precs

    law = json.loads(laws[0].read_text(encoding="utf-8"))
    assert law["law_name"] == "주택임대차보호법"
    assert law["articles"]
    assert law["source_url"].startswith("https://www.law.go.kr")

    prec = json.loads(precs[0].read_text(encoding="utf-8"))
    assert prec["case_no"]
    assert prec["source_url"].startswith("https://www.law.go.kr")
    assert prec["prec_id"]


_MULTI_LAW_SEARCH = """<?xml version="1.0" encoding="UTF-8"?>
<LawSearch>
  <law><법령명한글>난민법</법령명한글><법령일련번호>188376</법령일련번호></law>
  <law><법령명한글>민법</법령명한글><법령일련번호>284415</법령일련번호></law>
</LawSearch>"""


def test_collect_picks_exact_name_match_not_first_result(tmp_path, fixtures_dir):
    # 실 API는 "민법" 검색 시 "난민법"을 먼저 반환한다. 정확히 일치하는
    # 법령을 골라야 하며, 첫 결과(난민법)를 집어선 안 된다.
    fetched_mst = []

    class NameMatchClient(StubClient):
        def search(self, *, target, query, display=20):
            if target == "law":
                return _MULTI_LAW_SEARCH
            return super().search(target=target, query=query, display=display)

        def fetch(self, *, target, id):
            if target == "law":
                fetched_mst.append(id)
            return super().fetch(target=target, id=id)

    collect(client=NameMatchClient(fixtures_dir), out_dir=tmp_path,
            law_queries=["민법"], prec_queries=[])
    # 난민법(188376)이 아니라 민법(284415)을 fetch 해야 한다
    assert fetched_mst == ["284415"]


def test_collect_skips_prec_without_precservice_body(tmp_path, fixtures_dir):
    # 검색은 정상 결과를 주지만, 본문 fetch가 PrecService가 아닌 에러를 줄 때 건너뛴다
    class BadBodyClient(StubClient):
        def fetch(self, *, target, id):
            if target == "prec":
                return "<Law>일치하는 판례가 없습니다.</Law>"
            return super().fetch(target=target, id=id)

    collect(client=BadBodyClient(fixtures_dir), out_dir=tmp_path,
            law_queries=["주택임대차보호법"], prec_queries=["임대차 보증금 반환"])
    precs = list((tmp_path / "prec").glob("*.json"))
    assert precs == []   # PrecService 본문이 없으면 아무 파일도 안 쓴다
