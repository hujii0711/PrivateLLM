import re

_SOFT_HYPHEN = "­"
_NBSP = " "


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace(_SOFT_HYPHEN, "")
    text = text.replace(_NBSP, " ")          # nbsp → space
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 줄 단위로 내부 공백 축약 + 빈 줄 제거
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)
