import re

_SOFT_HYPHEN = "­"
_NBSP = " "


def normalize_text(text: str) -> str:
    """색인 전에 본문 텍스트의 보이지 않는 문자와 공백을 정리한다.

    법령/판례 XML에서 넘어온 특수 공백, 소프트 하이픈, 줄바꿈 차이를
    통일해 같은 내용이 안정적으로 임베딩되도록 만든다. 문단 구조는 줄바꿈으로
    남기되 빈 줄과 줄 안의 중복 공백은 제거한다.
    """
    # not text — text가 None, "", 0 등 falsy 값이면 True
    # 빈 값이 들어오면 바로 "" 반환하고 함수 종료
    # 이후 코드에서 None으로 인한 오류를 방지하는 방어 코드
    if not text:
        return ""
    text = text.replace(_SOFT_HYPHEN, "")
    text = text.replace(_NBSP, " ")          # nbsp → space
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 줄 단위로 내부 공백 축약 + 빈 줄 제거

    # 1. 줄 단위로 분리
    #    text.split("\n")는 문자열을 줄바꿈("\n") 기준으로 잘라 리스트로 반환합니다.
    #    예: "안녕\n하세요".split("\n") → ["안녕", "하세요"]

    # 2. 각 줄의 공백/탭을 하나의 공백으로 축약
    #    re.sub(r"[ \t]+", " ", ln)는 정규표현식을 사용하여 공백(space)이나 탭(\t)이 하나 이상 연속된 부분을 하나의 공백으로 치환합니다.
    #    예: "안녕    하세요".strip() → "안녕하세요"

    # 3. 줄 앞뒤 공백 제거
    #    .strip() 메서드는 문자열의 시작과 끝에 있는 공백(스페이스, 탭 등)을 제거합니다.
    #    예: "   안녕".strip() → "안녕"

    # 4. 결과를 리스트로 수집
    #    [...]는 리스트 컴프리헨션으로, for 루프의 결과를 모아 새로운 리스트를 만듭니다.
    #    위의 세 단계를 한 줄로 표현한 것입니다.
    #    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]

    # 5. 빈 줄 제거
    #    lines = [ln for ln in lines if ln]

    # 6. 문자열 합치기
    #    "\n".join(lines)는 리스트의 요소들을 "\n"으로 연결하여 하나의 문자열로 만듭니다.
    #    예: ["안녕", "하세요"].join("\n") → "안녕하세요"
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)
    # 입력 텍스트
    #     ↓
    # 빈 값이면 즉시 "" 반환
    #     ↓
    # 소프트 하이픈 제거
    #     ↓
    # 특수 공백 → 일반 공백
    #     ↓
    # 줄바꿈 문자 \n 으로 통일
    #     ↓
    # 줄 단위 분리 → 내부 공백 축약 → 앞뒤 공백 제거
    #     ↓
    # 빈 줄 제거
    #     ↓
    # \n 으로 다시 합쳐서 반환