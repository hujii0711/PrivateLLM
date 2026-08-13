# pipelines

주택임대차 보증금 반환 챗봇의 데이터 파이프라인.

## 설치
    cd pipelines
    uv sync

## 환경
    cp .env.example .env   # LAW_API_OC 채우기

## 실행
    uv run python -m pipelines.ingest.fetch_corpus   # 수집 → data/raw
    uv run python -m pipelines.chunk.chunker         # 청킹 → data/chunks
    uv run python -m pipelines.index.build_index     # 색인 → data/chroma
    uv run python -m pipelines.cli.query "보증금을 못 받았어요"

## 테스트
    uv run pytest            # 빠른 테스트
    uv run pytest -m slow    # 모델/네트워크 포함

## 실제 실행 방법
cd /Users/fujii0711/Claude/PrivateLLM/pipelines
set -a
source .env
set +a
python -m pipelines.chunk.chunker

🛠️ 명령어 단계별 역할
1. set -a (Allexport 옵션 켜기)
역할: 이 명령 이후로 선언되거나 변경되는 모든 변수를 자동으로 export(하위 프로세스로 전달 가능하도록 설정) 하라는 셸(Shell) 옵션입니다.

왜 쓸까? 원래 파이썬 등에서 환경 변수를 읽으려면 export API_KEY="xyz"처럼 변수 앞에 일일이 export를 붙여야 합니다. set -a를 켜두면 이 번거로운 과정을 생략할 수 있습니다.

2. source .env (환경 변수 파일 읽기)
역할: .env 파일에 작성된 내용을 현재 터미널 창에 그대로 실행(적용)합니다.

왜 쓸까? 보통 .env 파일 안에는 DB_URL=localhost, API_KEY=abcdef 같은 설정값들이 들어있습니다. source 명령어를 통해 이 값들을 현재 셸의 변수로 로딩합니다. 이때 앞서 켜둔 set -a 덕분에 모든 변수가 자동으로 export 상태가 됩니다.

3. set +a (Allexport 옵션 끄기)
역할: 자동 export 기능을 다시 비활성화(기본 상태로 복구) 합니다.

왜 쓸까? 이 옵션을 계속 켜두면, 이후에 터미널에서 임시로 만드는 일반 변수들까지 전부 환경 변수로 자동 등록되어 버립니다. 시스템 오작동이나 메모리 낭비를 방지하기 위해 깔끔하게 뒷정리를 하는 것입니다.


---


cd /Users/fujii0711/Claude/PrivateLLM/pipelines
uv sync

# .env 파일 확인/생성
cp .env.example .env
# 그다음 .env 안에 아래처럼 넣기
# LAW_API_OC=your_api_key

set -a
source .env
set +a

uv run python -m pipelines.ingest.fetch_corpus