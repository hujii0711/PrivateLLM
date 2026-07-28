"""A/B 비교: baseline vs qlora 평가 요약 → 지표별 델타 + 마크다운.

이 모듈은 파인튜닝(QLoRA) 전후 모델의 평가 결과를 비교하는 역할을 합니다.

A/B 비교란?
  - A(baseline): 파인튜닝하기 전 원본 모델의 평가 결과
  - B(qlora)   : QLoRA로 파인튜닝한 후 모델의 평가 결과
  - delta(Δ)   : B - A, 즉 파인튜닝으로 얼마나 성능이 향상됐는지의 차이

흐름:
  1. baseline.json, qlora.json 파일에서 요약(summary) 지표를 읽는다.
  2. 지표별로 delta(차이)를 계산한다.
  3. 결과를 마크다운 표 형식으로 출력한다.
"""
import json
from pathlib import Path

# 비교할 평가 지표 목록
# 각 지표의 의미:
#   recall_at_k       - 검색 단계에서 정답 문서가 상위 k개 안에 들어온 비율
#   citation_rate     - 답변에 [n] 형식의 인용이 포함된 비율
#   structure_rate    - 상담형 구조(도입·본문·결론)를 갖춘 답변 비율
#   disclaimer_rate   - 법적 면책 고지가 포함된 답변 비율
#   sources_rate      - 출처 목록이 명시된 답변 비율
#   mention_coverage  - 필수 언급 키워드를 얼마나 포함했는지의 비율
#   groundedness      - 답변이 검색된 문서(근거)에 충실한 정도 (0~1)
_METRICS = [
    "recall_at_k",
    "citation_rate",
    "structure_rate",
    "disclaimer_rate",
    "sources_rate",
    "mention_coverage",
    "groundedness",
]


def load_summary(path) -> dict:
    """평가 결과 JSON 파일에서 'summary' 섹션만 읽어 반환합니다.

    평가 결과 파일(baseline.json, qlora.json)은 여러 섹션을 포함하지만,
    비교에 필요한 집계 지표는 "summary" 키 안에 모여 있습니다.

    Args:
        path: 평가 결과 JSON 파일 경로 (str 또는 Path).

    Returns:
        {"recall_at_k": 0.82, "citation_rate": 0.91, ...} 형태의 딕셔너리.

    예시 파일 구조:
        {
          "summary": {"recall_at_k": 0.82, "citation_rate": 0.91, ...},
          "details": [...]   ← 이 부분은 사용하지 않음
        }
    """
    # Path(path).read_text()로 파일 전체를 문자열로 읽고,
    # json.loads()로 파이썬 딕셔너리로 변환한 뒤 "summary" 값만 꺼냅니다.
    return json.loads(Path(path).read_text(encoding="utf-8"))["summary"]


def compare_runs(baseline: dict, qlora: dict) -> dict:
    """baseline과 qlora 요약 딕셔너리를 비교하여 지표별 delta를 계산합니다.

    _METRICS에 정의된 지표 중, 두 딕셔너리 모두에 존재하는 것만 비교합니다.
    (어느 한쪽에만 있는 지표는 건너뜁니다.)

    Args:
        baseline: 파인튜닝 전 모델의 요약 지표 딕셔너리.
        qlora:    QLoRA 파인튜닝 후 모델의 요약 지표 딕셔너리.

    Returns:
        지표별 비교 결과 딕셔너리. 예:
        {
          "recall_at_k": {"baseline": 0.75, "qlora": 0.82, "delta": 0.0700},
          "citation_rate": {"baseline": 0.80, "qlora": 0.91, "delta": 0.1100},
          ...
        }

    delta가 양수(+)이면 파인튜닝 후 성능이 향상된 것을,
    음수(-)이면 오히려 나빠진 것을 의미합니다.
    """
    out = {}  # 결과를 담을 빈 딕셔너리

    for m in _METRICS:
        # 두 딕셔너리 모두에 해당 지표가 있을 때만 비교합니다.
        if m in baseline and m in qlora:
            out[m] = {
                "baseline": baseline[m],           # 파인튜닝 전 수치
                "qlora": qlora[m],                 # 파인튜닝 후 수치
                # delta = qlora - baseline (양수 = 개선, 음수 = 저하)
                # round(..., 4)로 소수점 4자리까지만 표시해 깔끔하게 출력
                "delta": round(qlora[m] - baseline[m], 4),
            }
    return out


def to_markdown(comparison: dict) -> str:
    """비교 결과 딕셔너리를 마크다운 표(table) 문자열로 변환합니다.

    출력 예시:
        | 지표            | baseline | qlora | Δ      |
        |----------------|----------|-------|--------|
        | recall_at_k    | 0.750    | 0.820 | +0.070 |
        | citation_rate  | 0.800    | 0.910 | +0.110 |

    Args:
        comparison: compare_runs()가 반환한 비교 결과 딕셔너리.

    Returns:
        마크다운 표 형식의 문자열 (터미널 또는 마크다운 뷰어에서 표로 렌더링됨).
    """
    # 마크다운 표 헤더 행과 구분선 행을 먼저 추가합니다.
    lines = [
        "| 지표 | baseline | qlora | Δ |",
        "|---|---|---|---|",
    ]

    for m, v in comparison.items():
        # f-문자열 포맷 설명:
        #   {v['baseline']:.3f} → 소수점 3자리로 표시 (예: 0.750)
        #   {v['delta']:+.3f}   → 부호(+/-) 포함 소수점 3자리 (예: +0.070, -0.020)
        lines.append(
            f"| {m} | {v['baseline']:.3f} | {v['qlora']:.3f} | {v['delta']:+.3f} |"
        )

    # 각 행을 줄바꿈(\n)으로 연결해 하나의 문자열로 만듭니다.
    return "\n".join(lines)
