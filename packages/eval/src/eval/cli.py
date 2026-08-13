"""
cli.py — 평가(Evaluation) 라이브 실행 진입점

【이 파일이 하는 일】
eval_set.jsonl 의 모든 질문을 실제 Retriever + MlxLLM 으로 실행하고,
결과를 data/eval_runs/{label}.json 파일로 저장합니다.

【실행 방법】
    # 기본 실행 (label=baseline):
    $ uv run --package eval python -m eval.cli

    # LoRA 어댑터 적용 결과를 qlora 레이블로 저장:
    $ uv run --package eval python -m eval.cli --label qlora --adapter ./data/adapters/qlora

    # 레이블 비교 (A/B 결과 보기):
    $ uv run --package finetune python -m finetune.compare_cli

【A/B 평가 (Baseline vs QLoRA)】
  --adapter 없이 실행 → baseline.json 생성
  --adapter 있이 실행 → qlora.json 생성
  두 파일을 compare_cli 로 비교해 파인튜닝 효과를 수치로 확인합니다.

【Judge 모델 공정성】
  답변 생성(gen_llm)은 어댑터를 적용한 모델을 사용하지만,
  품질 평가(judge_llm)는 항상 기본 모델(어댑터 없음)을 사용합니다.
  judge 모델이 다르면 점수 기준 자체가 달라져 공정한 비교가 불가능하기 때문입니다.

출력 파일:
    data/eval_runs/{label}.json
        {
            "label": "baseline",
            "summary": {...},   ← report.aggregate() 결과
            "items": [...]      ← 항목별 상세 결과
        }
"""

import json  # JSON 직렬화
import sys  # 커맨드라인 인자(sys.argv) 접근
from pathlib import Path

from api.llm import MlxLLM  # 실제 LLM (Apple Silicon MLX)
from api.settings import Settings  # 전역 설정
from rag.retriever import Retriever  # 벡터 DB 검색

from .dataset import load_eval_set  # 평가셋 로더
from .report import aggregate  # 지표 집계
from .runner import run_item  # 항목별 평가 실행

# ──────────────────────────────────────────────────────────
# 경로 상수
# ──────────────────────────────────────────────────────────
# 이 파일(cli.py) 기준으로 상위 2번째 디렉터리 = packages/eval/
# 그 아래 eval_set.jsonl 이 위치합니다.
_EVAL_SET = Path(__file__).resolve().parents[2] / "eval_set.jsonl"

# 레포 루트 계산 (parents[4] = PrivateLLM/)
_REPO_ROOT = Path(__file__).resolve().parents[4]

# 평가 결과 저장 디렉터리
_OUT_DIR = _REPO_ROOT / "data" / "eval_runs"


def main() -> None:
    """평가 라이브 실행 메인 함수.

    커맨드라인 인자:
        --label   : 결과 파일 이름 레이블 (기본값: "baseline")
                    $ python -m eval.cli --label qlora → qlora.json 저장
        --adapter : LoRA 어댑터 경로 (없으면 기본 모델 사용)
                    $ python -m eval.cli --adapter ./data/adapters/qlora
    """
    # ── 커맨드라인 인자 파싱 ──────────────────────────────
    # sys.argv : ["eval/cli.py", "--label", "qlora", "--adapter", "./path"] 같은 리스트
    label = "baseline"
    if "--label" in sys.argv:
        # "--label" 다음 항목이 레이블 값입니다.
        label = sys.argv[sys.argv.index("--label") + 1]

    # ── LLM 및 Retriever 초기화 ───────────────────────────
    settings = Settings.from_env()  # 환경 변수에서 설정 로드
    retriever = Retriever(settings.rag)  # 벡터 DB 연결

    # LoRA 어댑터 경로 파싱 (없으면 None → 기본 모델 사용)
    adapter = sys.argv[sys.argv.index("--adapter") + 1] if "--adapter" in sys.argv else None

    # 답변 생성용 LLM: 어댑터가 있으면 파인튜닝 모델, 없으면 기본 모델
    gen_llm = MlxLLM(settings.mlx_model, adapter_path=adapter)

    # Judge LLM: 항상 기본 모델 고정 (공정 비교를 위해)
    # 어댑터가 없으면 gen_llm 과 같은 모델이므로 인스턴스를 재사용합니다 (메모리 절약).
    # 어댑터가 있으면 파인튜닝 모델과 별도의 기본 모델 인스턴스를 생성합니다.
    judge_llm = gen_llm if adapter is None else MlxLLM(settings.mlx_model)

    # judge_fn: 프롬프트 문자열 → LLM 응답 문자열을 반환하는 함수
    # max_tokens=16 : 점수("0.8" 같은 짧은 숫자)만 필요하므로 토큰 수를 최소화합니다.
    # temperature=0.0 : 결정론적 응답 (항상 같은 점수를 부여하도록)
    def judge_fn(prompt):
        return "".join(
            judge_llm.stream(
                [{"role": "user", "content": prompt}],
                max_tokens=16,
                temperature=0.0,
            )
        )

    # ── 평가 실행 루프 ─────────────────────────────────────
    items = load_eval_set(_EVAL_SET)  # 평가셋 로드
    results = []

    for i, item in enumerate(items, 1):
        # 평가 항목 1개 실행 (검색 + 답변 생성 + 지표 계산)
        res = run_item(
            item,
            retriever=retriever,
            llm=gen_llm,
            judge_fn=judge_fn,
            top_k=settings.rag.top_k,
        )
        results.append(res)

        # 진행 상황을 터미널에 실시간 출력합니다.
        # 예: "[1/20] q1 hit=True cite=True ground=0.85"
        print(
            f"[{i}/{len(items)}] {item.id} "
            f"hit={res.retrieval_hit} "
            f"cite={res.metrics['has_citation']} "
            f"ground={res.groundedness:.2f}"
        )

    # ── 결과 저장 ─────────────────────────────────────────
    # 전체 지표 집계 계산
    agg = aggregate(results)

    # 출력 디렉터리 생성 (없으면 자동 생성)
    # parents=True : 중간 디렉터리도 함께 생성
    # exist_ok=True : 이미 존재해도 오류 없음
    _OUT_DIR.mkdir(parents=True, exist_ok=True)

    out = _OUT_DIR / f"{label}.json"

    # JSON 파일로 저장
    # ensure_ascii=False : 한글을 유니코드 이스케이프(\uXXXX) 없이 그대로 저장
    # indent=2           : 2칸 들여쓰기로 보기 좋게 포맷
    out.write_text(
        json.dumps(
            {
                "label": label,
                "summary": agg,
                "items": [
                    {
                        "id": r.id,
                        "retrieval_hit": r.retrieval_hit,
                        "metrics": r.metrics,
                        "groundedness": r.groundedness,
                        "answer": r.answer,
                    }
                    for r in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 최종 요약을 터미널에 출력합니다.
    print(f"\n=== {label} 요약 ===")
    print(json.dumps(agg, ensure_ascii=False, indent=2))
    print(f"저장: {out}")


# ──────────────────────────────────────────────────────────
# 직접 실행 진입점
# python -m eval.cli 로 실행하면 main() 이 호출됩니다.
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
