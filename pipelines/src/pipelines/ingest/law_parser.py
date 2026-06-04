"""국가법령정보센터 lawService.do(target=law) XML 파서.

실제 응답 구조(Task 4 fixture로 확인): 법령 > 기본정보 > 법령명_한글,
법령 > 조문 > 조문단위 > (조문번호, 조문제목, 조문내용, ...).
"""
from lxml import etree

_NAME = "법령명_한글"
_UNIT = "조문단위"
_NO = "조문번호"
_TITLE = "조문제목"


def parse_law(xml_text: str) -> dict:
    root = etree.fromstring(xml_text.encode("utf-8"))

    name_el = root.find(f".//{_NAME}")
    law_name = (name_el.text or "").strip() if name_el is not None else ""

    articles = []
    for unit in root.iter(_UNIT):
        no = _text(unit.find(_NO))
        if not no:
            continue
        title = _text(unit.find(_TITLE))
        # 조문내용 + 모든 하위 텍스트를 합쳐 본문 구성(항/호 포함)
        parts = [t.strip() for t in unit.itertext() if t and t.strip()]
        text = "\n".join(dict.fromkeys(parts))  # 순서 유지 중복 제거
        articles.append({
            "article_no": _normalize_no(no),
            "title": title,
            "text": text,
        })
    return {"law_name": law_name, "articles": articles}


def _text(el) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def _normalize_no(no: str) -> str:
    no = no.strip()
    return no if no.startswith("제") else f"제{no}조"
