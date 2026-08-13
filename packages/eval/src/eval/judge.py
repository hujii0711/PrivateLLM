"""
judge.py — LLM-as-Judge: LLM 자신이 답변 품질을 0~1 점수로 평가하는 모듈

【LLM-as-Judge 란?】
또 다른 LLM(또는 같은 LLM)이 "심판(Judge)" 역할을 맡아 답변 품질을 평가하는 기법입니다.
규칙 기반(answer_metrics.py) 으로 잡기 어려운 의미론적 품질을 측정할 수 있습니다.

장점:
  - "답변이 근거에 기반했는가"(Groundedness) 같은 고수준 판단 가능
  - 키워드 매칭으로는 포착하기 어려운 오류(사실 왜곡 등) 감지

단점:
  - LLM 호출 비용 발생
  - 판단 결과가 확률적(동일 입력에 다른 점수 가능)
  - 공정한 비교를 위해 judge 모델을 고정해야 함 (cli.py 참조)

【Groundedness(근거성) 란?】
LLM 답변이 검색된 법령·판례 근거에 충실한지를 나타내는 지표입니다.
근거에 없는 내용을 단정하면 낮은 점수, 근거에 충실하면 높은 점수가 부여됩니다.

【공정 비교를 위한 Judge 모델 고정】
baseline(기본 모델)과 qlora(파인튜닝 모델)를 비교할 때,
judge 모델은 항상 기본 모델을 사용합니다 (cli.py 의 judge_llm 참조).
judge 모델이 다르면 점수 기준이 달라져 공정한 A/B 비교가 불가능합니다.
"""

import re  # 정규식: 점수 숫자 추출에 사용
from collections.abc import Callable  # 함수 타입 힌트

# ──────────────────────────────────────────────────────────
# Judge LLM 에게 전달할 프롬프트 힌트 (고정 지시문)
# ──────────────────────────────────────────────────────────
JUDGE_PROMPT_HINT = (
    "아래 '근거'만으로 '답변'의 사실 진술이 뒷받침되는지 0.0~1.0 사이 숫자로만 평가하세요. "
    "근거에 없는 내용을 단정하면 낮게 점수를 줍니다."
)

# 응답에서 숫자를 추출하는 정규식
# \d+       : 하나 이상의 숫자
# (?:\.\d+)?: 선택적 소수점 이하 부분 (있어도 되고 없어도 됨)
# →  "0.8", "1", "0.75" 같은 숫자를 찾습니다.
_NUM = re.compile(r"\d+(?:\.\d+)?")


def build_judge_prompt(question: str, answer: str, contexts: list[str]) -> str:
    """Judge LLM 에게 전달할 평가 프롬프트 문자열을 조립합니다.

    조립 형식:
        {JUDGE_PROMPT_HINT}

        [질문]
        {question}

        [근거]
        - 근거1 본문
        - 근거2 본문

        [답변]
        {answer}

        점수(0.0~1.0):

    Args:
        question : 사용자가 입력한 원래 질문
        answer   : LLM 이 생성한 답변 (평가 대상)
        contexts : 검색된 법령·판례 본문 텍스트 목록 (Retrieved.text 값들)

    Returns:
        Judge LLM 에 전달할 완성된 프롬프트 문자열
    """
    # 각 근거 앞에 "- " 불릿을 붙여 읽기 좋게 포맷합니다.
    ctx = "\n".join(f"- {c}" for c in contexts)

    # f-string 으로 템플릿 조립
    return (
        f"{JUDGE_PROMPT_HINT}\n\n"
        f"[질문]\n{question}\n\n"
        f"[근거]\n{ctx}\n\n"
        f"[답변]\n{answer}\n\n"
        f"점수(0.0~1.0):"
    )


def groundedness_score(
    *,  # 모든 인자를 키워드 인자로 강제
    question: str,  # 평가할 질문
    answer: str,  # 평가할 답변
    contexts: list[str],  # 답변의 근거가 된 문서 본문 목록
    judge_fn: Callable[[str], str],  # LLM 호출 함수 (프롬프트 → 텍스트 응답)
) -> float:
    """Judge LLM 을 호출해 답변의 근거성(Groundedness) 점수를 반환합니다.

    처리 흐름:
      1. build_judge_prompt() 로 평가 프롬프트 생성
      2. judge_fn(prompt) 으로 LLM 에 평가 요청 → "0.8" 같은 텍스트 응답 수신
      3. 응답에서 숫자를 정규식으로 추출
      4. 0.0 ~ 1.0 범위로 클리핑하여 반환

    Args:
        question   : 사용자 질문
        answer     : 평가할 LLM 답변
        contexts   : 검색된 근거 문서 본문 목록
        judge_fn   : 프롬프트를 받아 LLM 응답 텍스트를 반환하는 함수
                     실제 사용 예 (cli.py):
                         judge_fn = lambda prompt: "".join(llm.stream([...]))

    Returns:
        0.0 ~ 1.0 사이의 근거성 점수
        (LLM 이 숫자를 반환하지 않으면 기본값 0.0 반환)
    """
    # Step 1: 평가 프롬프트 생성 후 LLM 에 전달
    out = judge_fn(build_judge_prompt(question, answer, contexts))

    # Step 2: LLM 응답에서 첫 번째 숫자 추출
    # _NUM.search(out) : 첫 번째 숫자 매치를 찾습니다.
    m = _NUM.search(out)

    if not m:
        # 숫자를 찾지 못하면 0.0 반환 (LLM 이 예상치 못한 형식으로 응답한 경우)
        return 0.0

    # Step 3: 문자열 숫자 → float 변환 후 0.0 ~ 1.0 범위로 클리핑
    # max(0.0, ...) : 음수 방지
    # min(1.0, ...) : 1.0 초과 방지
    return max(0.0, min(1.0, float(m.group(0))))
