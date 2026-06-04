"""국가법령정보센터 lawService.do(target=prec) XML 파서."""
import re

from lxml import etree

# <br>, <br/>, <br /> (대소문자/공백 무시) → 줄바꿈. 다른 각괄호 마커(<1989.12.30> 등)는 보존.
_BR = re.compile(r"(?i)<br\s*/?>")


def parse_prec(xml_text: str) -> dict:
    root = etree.fromstring(xml_text.encode("utf-8"))
    return {
        "case_name": _t(root, "사건명"),
        "case_no": _t(root, "사건번호"),
        "court": _t(root, "법원명"),
        "decided_on": _t(root, "선고일자"),
        "holding_summary": _t(root, "판시사항"),
        "judgment_summary": _t(root, "판결요지"),
        "body": _t(root, "판례내용"),
    }


def _t(root, tag: str) -> str:
    el = root.find(f".//{tag}")
    if el is None:
        return ""
    # 일부 요소는 HTML/줄바꿈을 포함 → 모든 하위 텍스트 결합
    text = "".join(el.itertext())
    text = _BR.sub("\n", text)
    return text.strip()
