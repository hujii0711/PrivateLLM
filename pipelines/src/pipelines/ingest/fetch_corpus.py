"""대상 법령·판례를 수집해 data/raw/{law,prec}/*.json 으로 저장한다."""

import json

# import re는 파이썬 표준 라이브러리인 정규 표현식(Regular Expression) 모듈을 가져오는 코드입니다.
# re 모듈은 특정한 규칙이나 패턴을 가진 문자열을 검색, 추출, 치환(변경)하는 강력한 텍스트 처리 기능을 제공합니다.
# 패턴 매칭: 이메일 주소, 전화번호, 공백 등 정해진 규격의 문자열 검사
# 문자열 치환 (re.sub): 패턴에 매칭되는 부분을 다른 문자열로 변경
# 문자열 분리 (re.split): 패턴을 기준으로 문자열 분리
import re
from pathlib import Path

# import lxml.etree as etree는 파이썬에서 XML 및 HTML 문서를 파싱(분석), 조작, 생성하기
# 위해 사용하는 고성능 라이브러리인 lxml의 etree 모듈을 가져오는 코드입니다.
# 국가법령정보센터(law.go.kr) API 등으로부터 받아온 XML 형식의 법령/판례 데이터를 파싱하여 원하는
# 정보를 추출하는 데 사용되고 있습니다.
import lxml.etree as etree

from ..config import Config
from .law_client import LawClient
from .law_parser import parse_law
from .prec_parser import parse_prec

LAW_QUERIES = ["주택임대차보호법", "민법"]
PREC_QUERIES = ["임대차 보증금 반환", "임차보증금 반환", "보증금 반환 동시이행"]

# {name}은 문자열 템플릿 플레이스홀더입니다.
# 이 줄은 일반 문자열이고, {name}은 지금 당장은 아무 역할도 없습니다.
# 나중에 .format()을 호출할 때 실제 값으로 치환되는 자리표시자입니다.
_LAW_URL = "https://www.law.go.kr/법령/{name}"
_PREC_URL = "https://www.law.go.kr/판례/{id}"


# 첫 번째 매개변수 자리에 위치한 *은 키워드 전용 인자 (Keyword-Only Arguments)를 강제하기 위한 문법
# * 기호 이후에 정의된 모든 매개변수(client, out_dir, law_queries, prec_queries)는 함수를 호출할 때
# 반드시 이름을 지정하는 키워드 인자 형태로만 전달해야 합니다.
# 순서에만 의존하는 위치 인자(Positional Argument)로는 전달할 수 없습니다.
def collect(*, client, out_dir: Path, law_queries=None, prec_queries=None) -> None:
    """법령/판례 검색어 목록을 순회하며 원천 데이터를 JSON 파일로 저장한다.

    법령은 검색어와 정확히 일치하는 법령을 우선 선택하고, 판례는 여러 검색어에서
    같은 판례가 중복으로 나올 수 있어 판례일련번호 기준으로 한 번만 저장한다.
    저장된 JSON은 `chunker`가 읽는 `raw/law`, `raw/prec` 입력 데이터가 된다.
    """

    out_dir = Path(out_dir)
    (out_dir / "law").mkdir(parents=True, exist_ok=True)
    (out_dir / "prec").mkdir(parents=True, exist_ok=True)

    for q in law_queries or LAW_QUERIES:
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
    #  ↑      ↑        ↑
    # 변수명  타입힌트  실제 값(초기화)
    for q in prec_queries or PREC_QUERIES:
        search_xml = client.search(target="prec", query=q, display=20)
        for pid in _all(search_xml, "판례일련번호"):
            if pid in seen:
                continue
            seen.add(pid)
            body_xml = client.fetch(target="prec", id=pid)
            if "<PrecService" not in body_xml:
                continue  # 본문이 없는 검색 결과는 건너뛴다
            prec = parse_prec(body_xml)
            if not prec["case_no"]:
                continue
            prec["prec_id"] = pid
            prec["source_url"] = _PREC_URL.format(id=pid)
            _write(out_dir / "prec" / f"{pid}.json", prec)


# _ 접두사내부용 함수 표시 (외부에서 직접 호출 비권장)
# search_xml: strXML 문자열 입력
# query: str검색할 법령명-> str | None
# 찾으면 문자열, 없으면 None 반환
def _match_law_mst(search_xml: str, query: str) -> str | None:
    """검색 결과 중 법령명이 질의어와 정확히 일치하는 법령일련번호를 고른다.

    실 API는 결과를 가나다순 등으로 정렬하므로 첫 결과가 질의어와 다를 수
    있다(예: "민법" 검색 시 "난민법"이 먼저). 정확히 일치하는 항목을 우선하고,
    없으면 첫 결과로 폴백한다. fixture는 단일 결과라 폴백 경로로 동작한다.
    """
    # search_xml 문자열을 바이너리로 인코딩한 후 etree.fromstring()을 통해 XML 트리 구조의
    # 루트 노드 객체로 변환합니다. --> XML 파싱
    # <body>
    #   <법령일람>
    #     <row>
    #       <법령명한글>민법</법령명한글>
    #       <법령일련번호>1001</법령일련번호>
    #     </row>
    #     <row>
    #       <법령명한글>민사소송법</법령명한글>
    #       <법령일련번호>1002</법령일련번호>
    #     </row>
    #   </법령일람>
    # </body>
    # 1. 문자열 → 바이트로 변환
    #    search_xml.encode("utf-8")
    # 2. 바이트 → XML 트리(루트 노드)로 변환
    #    etree.fromstring()
    root = etree.fromstring(search_xml.encode("utf-8"))  # 바이트로 변환된 XML을 파싱해서 Element 트리의 루트 노드를 반환합니다.
    # first_mst — 정확히 일치하는 결과가 없을 때 첫 번째 결과로 폴백하기 위한 변수
    first_mst = None
    # 실수로 공백이 포함된 검색어 방어
    want = query.strip()
    # 결과 행 단위로 (법령명한글, 법령일련번호) 쌍을 본다. law 검색 결과 루트
    # 바로 아래에 행 요소들이 있고, 각 행에 두 태그가 함께 들어 있다.
    # root.iter() — XML 트리의 모든 노드를 순서대로 순회
    # root.iter()는 XML 트리의 모든 하위 요소(Element)를 순회하는 이터레이터입니다.
    # root.iter()는 root 자기 자신부터 시작해서, 트리 구조 전체를 깊이 우선(depth-first) 순서로 하나씩 방문합니다. 즉 자식뿐 아니라 손자, 증손자까지 모든 하위 태그를 빠짐없이 훑습니다.
    # 각 row는 XML의 한 요소(태그)
    for row in root.iter():
        # .find("태그명") — 자식 요소 중 해당 태그를 찾아 반환, 없으면 None 반환
        name_el = row.find("법령명한글")
        mst_el = row.find("법령일련번호")
        # 조건 1: 태그 자체가 없음
        # mst_el is None
        # 조건 2: 태그는 있지만 텍스트가 없거나 공백뿐
        # not (mst_el.text and mst_el.text.strip())
        # 둘중 하나라도 해당하면 continue 수행함

        # 왜 == 대신 is를 쓰나?
        # mst_el is None    # ✅ 올바른 방식
        # mst_el == None    # ⚠️ 동작은 하지만 관례상 지양
        # None은 파이썬에서 유일한 싱글턴 객체라서, 값 비교(==)가 아니라 정체성 비교(is) 를 쓰는 것이 파이썬 표준 관례(PEP 8)입니다. is가 더 빠르고 명확합니다.

        if mst_el is None or not (mst_el.text and mst_el.text.strip()):
            continue
        # 루프에서 처음 만난 유효한 일련번호만 저장
        # if first_mst is None — 이미 저장됐으면 덮어쓰지 않음
        mst = mst_el.text.strip()
        if first_mst is None:
            first_mst = mst

        # 법령명 추출 — 삼항 표현식
        # if name_el is not None:        # 태그가 존재하면
        #     name = (name_el.text or "").strip()
        #     # name_el.text가 None이면 "" 사용, 있으면 공백 제거
        # else:                          # 태그가 없으면
        #     name = ""
        name = (name_el.text or "").strip() if name_el is not None else ""
        if name == want:
            return mst
    # 정확히 일치하는 결과가 없었다면 첫 번째 결과 반환
    # 결과가 아예 없었다면 None 반환
    return first_mst


def _write(path: Path, obj: dict) -> None:
    """dict 객체를 사람이 읽기 쉬운 UTF-8 JSON 파일로 저장한다."""

    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _all(xml_text: str, tag: str) -> list[str]:
    """XML 전체에서 특정 태그의 비어 있지 않은 텍스트 값을 모두 가져온다."""

    # xml_text 문자열을 XML 객체로 파싱합니다.
    root = etree.fromstring(xml_text.encode("utf-8"))
    # root.iter(tag)를 이용해 XML 문서 전체에서 지정한 태그(예: 판례일련번호 등)의
    # 텍스트 값들을 리스트로 한 번에 가져옵니다.
    return [e.text.strip() for e in root.iter(tag) if e.text and e.text.strip()]


def _slug(s: str) -> str:
    """파일명에 쓰기 좋도록 문자열 앞뒤 공백과 내부 공백을 정리한다."""

    return re.sub(r"\s+", "_", s.strip())  # re.sub(찾을패턴, 바꿀문자, 대상문자열)


def main() -> None:
    """환경 설정을 읽고 기본 검색어 세트로 원천 데이터를 수집한다."""
    # cfg에서 추가로 쓸 수 있는 것들 (property)
    # Config는 oc, data_root 외에도 @property로 정의된 파생 경로들을 제공합니다:
    cfg = Config.from_env()
    # cfg.oc          # "fujii0711" (환경변수에서 읽음)
    # cfg.data_root   # Path 객체 (환경변수 or 기본값)
    # cfg.raw_dir     # cfg.data_root / "raw"
    # cfg.chunks_dir  # cfg.data_root / "chunks"
    # cfg.chroma_dir  # cfg.data_root / "chroma"
    cfg.ensure_dirs()
    collect(client=LawClient(oc=cfg.oc), out_dir=cfg.raw_dir)
    print(f"수집 완료 → {cfg.raw_dir}")


if __name__ == "__main__":
    main()

# 전체 흐름 요약
# XML 문자열 → 파싱 → 루트 노드
#         ↓
# 모든 노드 순회
#         ↓
# 법령일련번호 없으면 건너뜀
#         ↓
# 첫 번째 유효한 일련번호 저장 (폴백용)
#         ↓
# 법령명 == 검색어 → 즉시 반환 ✅
#         ↓
# 끝까지 일치 없음 → 첫 번째 결과 반환 (폴백)
#                  → 결과 없음이면 None 반환

# uv run python -m pipelines.ingest.fetch_corpus
