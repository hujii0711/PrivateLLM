"""baseline.json vs qlora.json → A/B 결론 문서 출력.

실행: uv run --package finetune python -m finetune.compare_cli
"""
from pathlib import Path

from .compare import compare_runs, load_summary, to_markdown

_REPO_ROOT = Path(__file__).resolve().parents[4]
_RUNS = _REPO_ROOT / "data" / "eval_runs"


def main() -> None:
    base = load_summary(_RUNS / "baseline.json")
    qlora = load_summary(_RUNS / "qlora.json")
    cmp = compare_runs(base, qlora)
    print(to_markdown(cmp))


if __name__ == "__main__":
    main()
