"""국가법령정보센터 lawService.do(target=law) XML 파서.

실제 응답 구조(Task 4 fixture로 확인): 법령 > 기본정보 > 법령명_한글,
법령 > 조문 > 조문단위 > (조문번호, 조문제목, 조문내용, ...).
"""
from lxml import etree

_NAME = "법령명_한글"
_UNIT = "조문단위"
_NO = "조문번호"
_BRANCH_NO = "조문가지번호"  # 가지조문(제3조의2 등)의 가지번호. 일반 조문엔 없음.
_TITLE = "조문제목"

# 본문 텍스트를 구성할 때 사용할 콘텐츠 태그.
# 메타데이터(조문번호/조문여부/조문제목/조문시행일자/조문변경여부 등)는 제외한다.
_CONTENT = "조문내용"  # 조문 머리말/본문 (예: "제1조(목적) ...")
_HANG = "항"
_HANG_TEXT = "항내용"  # 항번호 마커(①)를 이미 포함한 항 본문
_HO = "호"
_HO_TEXT = "호내용"  # 호번호 마커(1.)를 이미 포함한 호 본문


def parse_law(xml_text: str) -> dict:
    root = etree.fromstring(xml_text.encode("utf-8"))

    name_el = root.find(f".//{_NAME}")
    law_name = (name_el.text or "").strip() if name_el is not None else ""

    articles = []
    for unit in root.iter(_UNIT):
        no = _text(unit.find(_NO))
        if not no:
            continue
        branch = _text(unit.find(_BRANCH_NO))
        title = _text(unit.find(_TITLE))
        articles.append({
            "article_no": _normalize_no(no, branch),
            "title": title,
            "text": _article_text(unit),
        })
    return {"law_name": law_name, "articles": articles}


def _article_text(unit) -> str:
    """조문단위에서 실제 본문(조문내용 + 항/호 내용)만 추출한다.

    메타데이터 형제 태그(조문번호/조문여부/조문시행일자/조문변경여부 등)는
    제외하고, 항내용/호내용은 이미 항번호(①)·호번호(1.) 마커를 포함하므로
    별도의 마커 태그(항번호/호번호)는 건너뛴다.
    """
    parts: list[str] = []

    body = _text(unit.find(_CONTENT))
    if body:
        parts.append(body)

    for hang in unit.findall(_HANG):
        hang_text = _text(hang.find(_HANG_TEXT))
        if hang_text:
            parts.append(hang_text)
        for ho in hang.findall(_HO):
            ho_text = _text(ho.find(_HO_TEXT))
            if ho_text:
                parts.append(ho_text)

    return "\n".join(parts)


def _text(el) -> str:
    return (el.text or "").strip() if el is not None and el.text else ""


def _normalize_no(no: str, branch: str = "") -> str:
    no = no.strip()
    base = no if no.startswith("제") else f"제{no}조"
    b = branch.strip()
    if b and b not in ("0", ""):
        return f"{base}의{b}"
    return base
