"""라이브 FT 데이터 빌드: 질문 풀 → 후보 생성 → 형식·근거 필터 → MLX chat JSONL.

이 파일은 파인튜닝(Fine-Tuning) 데이터셋을 자동으로 만드는 "메인 스크립트"입니다.
아래 5단계 파이프라인을 순서대로 실행합니다:

  1단계 [질문 로드]    : question_pool.jsonl에서 질문 목록을 읽어옵니다.
  2단계 [후보 생성]    : 각 질문마다 LLM으로 k개의 후보 답변을 생성합니다.
  3단계 [품질 필터링]  : 형식 요건 + 근거 점수 기준으로 후보를 걸러냅니다.
  4단계 [파일 저장]    : 채택된 예제를 train/valid JSONL로 나눠 저장합니다.
  5단계 [통계 출력]    : 전체 빌드 통계를 stats.json에 저장하고 터미널에 출력합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 실행 명령어 분해 설명
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  uv run --package ftdata python -m ftdata.cli [--k 6] [--per-q 2] [--min-ground 0.5]

  ┌ uv run
  │   uv가 관리하는 가상환경에서 명령을 실행합니다.
  │   필요한 의존성(패키지)이 없으면 자동으로 설치 후 실행합니다.
  │
  ├ --package ftdata
  │   이 워크스페이스 안의 여러 패키지 중 'ftdata' 패키지의 환경을 사용합니다.
  │
  ├ python -m ftdata.cli
  │   ftdata/cli.py 파일을 파이썬 모듈로 실행합니다.
  │   (python cli.py와 달리 패키지 경로가 올바르게 설정됩니다.)
  │
  ├ --k 6         : RAG 검색 시 가져올 관련 문서의 개수 (기본값 6)
  ├ --per-q 2     : 질문당 최종 채택할 최대 후보 답변 수 (기본값 2)
  └ --min-ground 0.5 : 채택 기준이 되는 근거 점수 최솟값 0.0~1.0 (기본값 0.5)

  ※ [대괄호]는 "선택 옵션"을 뜻하는 문서 표기입니다. 실제 실행 시에는 대괄호 없이 입력하세요.
     예) uv run --package ftdata python -m ftdata.cli --k 8 --per-q 3

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 출력 파일
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  data/ft/train.jsonl  → 학습에 사용할 예제 (전체의 약 90%)
  data/ft/valid.jsonl  → 검증에 사용할 예제 (10개 중 1개꼴로 분리)
  data/ft/stats.json   → 빌드 결과 통계 (질문 수, 통과율 등)
"""

import json
import sys
from pathlib import Path

# ── 외부 패키지 임포트 ────────────────────────────────────────────────────────
from api.llm import MlxLLM  # Apple Silicon(MLX)에서 LLM을 실행하는 클라이언트
from api.settings import Settings  # .env 파일이나 환경변수에서 설정값을 읽어오는 클래스
from rag.retriever import Retriever  # 벡터 DB에서 관련 문서를 검색하는 객체

# ── 같은 패키지 내 모듈 임포트 ────────────────────────────────────────────────
# "."은 현재 패키지(ftdata)를 의미하는 상대 경로 임포트입니다.
from .builder import split_train_valid, to_chat_example, write_jsonl
from .filter import format_ok
from .generate import generate_candidates
from .questions import load_questions

# ── 경로 상수 ─────────────────────────────────────────────────────────────────
# Path(__file__).resolve() → 현재 파일의 절대 경로
# .parents[4]             → 4단계 위 디렉토리 = 저장소(repo) 루트
_REPO_ROOT = Path(__file__).resolve().parents[4]

# 파인튜닝 데이터를 저장할 폴더: <repo 루트>/data/ft/
_OUT_DIR = _REPO_ROOT / "data" / "ft"


def _arg(name: str, default):
    """커맨드라인 인수(sys.argv)에서 특정 옵션 값을 읽어 반환하는 헬퍼 함수.

    파이썬은 sys.argv에 터미널 인수를 리스트로 저장합니다.
    예) "python -m ftdata.cli --k 8" 이라고 실행하면:
        sys.argv = ["...cli.py", "--k", "8"]

    이 함수는 그 리스트에서 name("--k")을 찾아 바로 다음 값("8")을 꺼내고,
    default와 같은 타입으로 변환합니다(예: int("8") → 8).

    Args:
        name:    찾을 옵션 이름. 예: "--k", "--per-q", "--min-ground"
        default: 옵션이 없을 때 사용할 기본값.
                 이 값의 타입(int, float 등)으로 자동 변환도 수행합니다.

    Returns:
        옵션이 있으면 default와 같은 타입으로 변환된 값, 없으면 default.
    """
    if name in sys.argv:
        # sys.argv.index(name) : 옵션 이름("--k")이 위치한 인덱스를 찾는다.
        # + 1                  : 그 바로 다음 칸이 값("8")이다.
        # type(default)(...)   : default가 int면 int("8")=8, float이면 float("0.5")=0.5
        return type(default)(sys.argv[sys.argv.index(name) + 1])
    return default  # 해당 옵션이 없으면 기본값을 그대로 반환


def main() -> None:
    """파인튜닝 데이터 빌드 파이프라인의 진입점(entry point).

    커맨드라인 옵션을 파싱한 뒤, 질문 풀 전체를 순회하며
    후보 답변을 생성하고 필터링하여 JSONL 파일로 저장합니다.
    """
    # ── 1단계: 커맨드라인 옵션 파싱 ──────────────────────────────────────────
    k = _arg("--k", 6)  # 검색할 관련 문서 수 (기본 6)
    per_q = _arg("--per-q", 2)  # 질문당 최대 채택 후보 수 (기본 2)
    min_ground = _arg("--min-ground", 0.5)  # 근거 점수 최솟값 (기본 0.5)

    # ── 2단계: 설정·모델·검색기 초기화 ────────────────────────────────────────
    settings = Settings.from_env()  # .env / 환경변수 → 설정 객체 생성
    retriever = Retriever(settings.rag)  # 벡터 DB 기반 문서 검색기 생성
    llm = MlxLLM(settings.mlx_model)  # MLX 언어 모델 로드 (Apple Silicon용)

    # judge_fn: 근거 점수를 계산할 때 사용하는 LLM 호출 래퍼 함수.
    # - max_tokens=16  : 판정 결과는 짧으면 충분하므로 최대 16 토큰만 생성
    # - temperature=0.0: 항상 동일한 판정이 나오도록 결정적(deterministic) 설정
    # "".join(...) : llm.stream()은 토큰을 하나씩 yield하므로 이어붙여 문자열로 만든다.
    def judge_fn(prompt):
        return "".join(
            llm.stream(
                [{"role": "user", "content": prompt}],
                max_tokens=16,
                temperature=0.0,
            )
        )

    # ── 3단계: 질문별 후보 생성 및 품질 필터링 ────────────────────────────────
    questions = load_questions()  # question_pool.jsonl에서 질문 목록 로드
    examples: list[dict] = []  # 최종 채택된 학습 예제 목록
    n_cand = n_pass = 0  # 통계 카운터: 총 후보 수 / 필터 통과 수

    # enumerate(questions, 1) : 1부터 시작하는 인덱스 i와 질문 q를 함께 순회
    for i, q in enumerate(questions, 1):
        # 질문 q 하나에 대해 k개의 후보 답변을 생성합니다.
        # hits  : 검색된 관련 문서 목록 (모든 후보가 공유)
        # cands : 생성된 Candidate 목록 (answer + sources + grounded 점수 포함)
        hits, cands = generate_candidates(
            q,
            retriever=retriever,
            llm=llm,
            judge_fn=judge_fn,
            k=k,
            temperature=0.7,  # 0.7 = 적당한 다양성 (0이면 매번 같은 답변)
        )
        n_cand += len(cands)  # 이번 질문에서 생성된 후보 수를 전체 카운터에 누적

        # 필터 조건 2가지를 동시에 만족하는 후보만 남깁니다.
        #   ① format_ok()     : 인용·구조·면책·출처 형식 요건 통과
        #   ② grounded >= min_ground : 근거 점수가 기준값 이상
        kept = [c for c in cands if format_ok(c.answer, sources=c.sources) and c.grounded >= min_ground]

        # 근거 점수(grounded)가 높은 순으로 정렬합니다.
        # reverse=True → 내림차순(높은 점수가 앞으로)
        kept.sort(key=lambda c: c.grounded, reverse=True)

        # 질문당 최대 per_q 개만 채택합니다.
        # 슬라이싱 [:per_q]으로 앞에서부터 잘라냅니다.
        kept = kept[:per_q]
        n_pass += len(kept)  # 통과한 후보 수 누적

        # 채택된 후보를 MLX chat 형식으로 변환하여 examples에 추가합니다.
        for c in kept:
            examples.append(to_chat_example(q, hits, c.answer))

        # 진행 상황을 터미널에 실시간으로 출력합니다.
        # 예: [3/20] kept 2/6 (총 5)  → 3번째 질문, 6개 후보 중 2개 채택, 누적 5개
        print(f"[{i}/{len(questions)}] kept {len(kept)}/{len(cands)} (총 {len(examples)})")

    # ── 4단계: train/valid 분할 및 JSONL 파일 저장 ────────────────────────────
    # 10번째, 20번째, ... 예제를 valid셋으로, 나머지를 train셋으로 분리합니다.
    train, valid = split_train_valid(examples, valid_every=10)

    _OUT_DIR.mkdir(parents=True, exist_ok=True)  # 출력 폴더가 없으면 자동 생성
    write_jsonl(_OUT_DIR / "train.jsonl", train)  # 학습셋 저장
    write_jsonl(_OUT_DIR / "valid.jsonl", valid)  # 검증셋 저장

    # ── 5단계: 빌드 통계 저장 및 터미널 출력 ─────────────────────────────────
    stats = {
        "questions": len(questions),  # 전체 질문 수
        "candidates": n_cand,  # 총 생성 후보 수
        "kept": n_pass,  # 필터 통과 후보 수
        "pass_rate": (n_pass / n_cand if n_cand else 0.0),  # 통과율 (0 나누기 방지)
        "train": len(train),  # train셋 예제 수
        "valid": len(valid),  # valid셋 예제 수
        "k": k,  # 사용한 --k 값
        "per_q": per_q,  # 사용한 --per-q 값
        "min_ground": min_ground,  # 사용한 --min-ground 값
    }

    # 통계를 JSON 파일로 저장 (indent=2: 들여쓰기 2칸, ensure_ascii=False: 한글 깨짐 방지)
    (_OUT_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 최종 요약을 터미널에 출력합니다.
    print("\n=== 빌드 요약 ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"저장: {_OUT_DIR}/train.jsonl, valid.jsonl, stats.json")


# ── 실행 진입점 ───────────────────────────────────────────────────────────────
# if __name__ == "__main__": 의 의미:
#   - 이 파일을 직접 실행(python cli.py 또는 python -m ftdata.cli)할 때 → main() 호출
#   - 다른 파일에서 import할 때(from ftdata import cli) → 이 블록은 실행되지 않음
# 이렇게 분리하면 테스트나 import 시에 의도치 않은 부작용을 막을 수 있습니다.
if __name__ == "__main__":
    main()
