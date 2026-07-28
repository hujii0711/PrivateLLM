"""baseline.json vs qlora.json → A/B 결론 문서 출력.

이 파일은 compare.py의 비교 기능을 커맨드라인에서 실행할 수 있도록
감싸주는 "진입점(entry point)" 스크립트입니다.

실행 방법:
  uv run --package finetune python -m finetune.compare_cli

동작:
  1. data/eval_runs/baseline.json 을 읽는다.
  2. data/eval_runs/qlora.json 을 읽는다.
  3. 두 파일의 지표를 비교하여 마크다운 표를 터미널에 출력한다.

출력 예시:
  | 지표           | baseline | qlora | Δ      |
  |----------------|----------|-------|--------|
  | recall_at_k    | 0.750    | 0.820 | +0.070 |
  | citation_rate  | 0.800    | 0.910 | +0.110 |
"""
from pathlib import Path

# 같은 패키지(finetune)의 compare 모듈에서 함수 3개를 가져옵니다.
from .compare import compare_runs, load_summary, to_markdown

# 저장소 루트 경로를 자동으로 계산합니다.
# 이 파일에서 4단계 위로 올라가면 repo 루트가 됩니다.
_REPO_ROOT = Path(__file__).resolve().parents[4]

# 평가 결과 파일들이 저장된 디렉토리 경로
# 예: /Users/.../PrivateLLM/data/eval_runs/
_RUNS = _REPO_ROOT / "data" / "eval_runs"


def main() -> None:
    """baseline과 qlora 평가 결과를 비교하여 마크다운 표로 터미널에 출력합니다.

    각 단계:
      1. load_summary()  → JSON 파일에서 요약 지표 딕셔너리 로드
      2. compare_runs()  → 두 딕셔너리의 지표별 delta 계산
      3. to_markdown()   → 비교 결과를 마크다운 표 문자열로 변환
      4. print()         → 터미널에 출력
    """
    # baseline(파인튜닝 전) 평가 결과 로드
    base = load_summary(_RUNS / "baseline.json")

    # qlora(파인튜닝 후) 평가 결과 로드
    qlora = load_summary(_RUNS / "qlora.json")

    # 두 결과를 지표별로 비교 (delta 포함)
    cmp = compare_runs(base, qlora)

    # 마크다운 표 형식으로 변환하여 출력
    print(to_markdown(cmp))


# 이 파일을 직접 실행할 때만 main()을 호출합니다.
# 다른 모듈에서 import할 때는 실행되지 않습니다.
if __name__ == "__main__":
    main()
