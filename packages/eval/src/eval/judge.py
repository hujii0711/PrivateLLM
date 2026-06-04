"""LLM-as-judge: 답변이 검색 근거에 기반했는지 0~1 점수화. judge_fn 주입 가능."""
import re
from typing import Callable

JUDGE_PROMPT_HINT = (
    "아래 '근거'만으로 '답변'의 사실 진술이 뒷받침되는지 0.0~1.0 사이 숫자로만 평가하세요. "
    "근거에 없는 내용을 단정하면 낮게 점수를 줍니다."
)

_NUM = re.compile(r"\d+(?:\.\d+)?")


def build_judge_prompt(question: str, answer: str, contexts: list[str]) -> str:
    ctx = "\n".join(f"- {c}" for c in contexts)
    return (f"{JUDGE_PROMPT_HINT}\n\n[질문]\n{question}\n\n[근거]\n{ctx}\n\n"
            f"[답변]\n{answer}\n\n점수(0.0~1.0):")


def groundedness_score(*, question: str, answer: str, contexts: list[str],
                       judge_fn: Callable[[str], str]) -> float:
    out = judge_fn(build_judge_prompt(question, answer, contexts))
    m = _NUM.search(out)
    if not m:
        return 0.0
    return max(0.0, min(1.0, float(m.group(0))))
