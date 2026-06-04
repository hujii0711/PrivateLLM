"""상담형 RAG 프롬프트 조립. 시스템 프롬프트 + 번호 매긴 근거 + 사용자 질문."""
from .types import Retrieved

SYSTEM_PROMPT = (
    "당신은 대한민국 주택임대차(특히 보증금 반환) 문제를 돕는 상담 도우미입니다. "
    "아래 '근거' 자료만 사용해 답하세요. 답변은 ① 상황 요약 ② 적용 법리 ③ 다음 절차 "
    "순의 상담형으로 작성합니다. 사실을 진술할 때는 반드시 해당 근거 번호를 [1], [2]처럼 "
    "문장 끝에 답니다. 근거에 없는 내용은 추측하지 말고, 근거가 부족하면 그 사실을 밝히세요. "
    "이 답변은 일반적 정보 제공이며 법률 자문이 아님을 마지막 줄에 고지하세요."
)


def build_messages(query: str, hits: list[Retrieved]) -> list[dict]:
    blocks = []
    for i, h in enumerate(hits, 1):
        blocks.append(f"[{i}] ({h.title}) {h.text}")
    grounds = "\n\n".join(blocks) if blocks else "(관련 근거 없음)"
    user = f"근거:\n{grounds}\n\n질문: {query}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
