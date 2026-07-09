"""국가법령정보센터 lawService.do(target=prec) XML 파서."""

import re

import lxml.etree as etree

# <br>, <br/>, <br /> (대소문자/공백 무시) → 줄바꿈. 다른 각괄호 마커(<1989.12.30> 등)는 보존.
_BR = re.compile(r"(?i)<br\s*/?>")


def parse_prec(xml_text: str) -> dict:
    """판례 본문 XML을 파이프라인용 판례 dict로 변환한다.

    검색과 인용에 필요한 사건명, 사건번호, 법원명, 선고일자, 판시사항,
    판결요지, 본문을 고정된 키로 추출해 이후 수집/청킹 단계가 XML 구조를
    다시 몰라도 되게 만든다.
    """

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

# rootXML 루트 노드 (타입 힌트 생략)
# tag: str찾을 태그명 문자열
# -> str항상 문자열 반환 (None 없음)
def _t(root, tag: str) -> str:
    """지정한 태그의 전체 텍스트를 줄바꿈까지 보존해 추출한다.

    판례 필드는 내부에 `<br>`이나 하위 요소가 섞일 수 있으므로 itertext로
    모든 텍스트를 합치고, HTML 줄바꿈 표기는 실제 줄바꿈 문자로 바꾼다.
    """

    el = root.find(f".//{tag}")
    if el is None:
        return ""
    # 일부 요소는 HTML/줄바꿈을 포함 → 모든 하위 텍스트 결합
    # el.text 만 쓰면 → "첫 번째 내용" 만 가져옴 ❌
    # el.itertext() 쓰면 → ["첫 번째 내용", "두 번째 내용", "세 번째 내용"] ✅
    text = "".join(el.itertext())
    # _BR — 코드 상단에 정의된 정규식 패턴 (컴파일된 regex 객체)
    # .sub("\n", text) — 매칭되는 부분을 \n으로 치환
    text = _BR.sub("\n", text)
    return text.strip()
# 전체 흐름 요약
# 태그명으로 XML 탐색 (깊이 무관)
#         ↓
# 태그 없으면 "" 반환
#         ↓
# itertext()로 모든 하위 텍스트 수집
#         ↓
# "".join()으로 하나의 문자열로 합침
#         ↓
# <br> → \n 으로 치환
#         ↓
# 앞뒤 공백 제거 후 반환