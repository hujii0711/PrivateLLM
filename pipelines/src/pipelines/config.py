import os

# dataclass — 클래스를 데이터 컨테이너로 간편하게 정의하는 데코레이터
from dataclasses import dataclass

# Path — 문자열 대신 객체로 파일 경로를 다루는 클래스
from pathlib import Path

# __file__ — 현재 파일의 경로
# .resolve() — 절대 경로로 변환
# .parents[3] — 3단계 상위 폴더 (예: a/b/c/d/config.py → a/)
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


# @dataclass는 __init__, __repr__ 등을 자동 생성해 줍니다. 즉, 아래가 자동으로 만들어집니다
# ========================
# def __init__(self, data_root: Path, oc: str):
#     self.data_root = data_root
#     self.oc = oc
# ========================
@dataclass
class Config:
    """파이프라인 실행에 필요한 경로와 외부 API 인증값을 모은 설정 객체."""

    data_root: Path
    oc: str

    # @property는 메서드를 속성처럼 접근하게 해 줍니다.
    # pythonconfig.raw_dir()  # ❌ 괄호 필요 없음
    # config.raw_dir    # ✅ 이렇게 접근
    @property
    def raw_dir(self) -> Path:
        """수집 단계가 원천 JSON을 저장하고 이후 단계가 읽는 디렉터리."""
        return self.data_root / "raw"

    @property
    def chunks_dir(self) -> Path:
        """청킹 단계가 jsonl 산출물을 저장하는 디렉터리."""
        return self.data_root / "chunks"

    @property
    def chroma_dir(self) -> Path:
        """Chroma 영속 색인을 저장하는 디렉터리."""
        return self.data_root / "chroma"

    def ensure_dirs(self) -> None:
        """파이프라인 산출물 디렉터리를 미리 생성한다."""
        # 세 개를 튜플로 묶어서 순회한다.
        for d in (self.raw_dir, self.chunks_dir, self.chroma_dir):
            # parents=True — 중간 폴더가 없어도 자동 생성
            # exist_ok=True — 이미 폴더가 있어도 오류 없이 통과
            d.mkdir(parents=True, exist_ok=True)

    # @classmethod는 self 대신 cls(클래스 자체)를 받습니다
    # 팩토리 메서드 패턴 — 환경변수에서 값을 읽어 Config 인스턴스를 생성하는 대안 생성자
    # os.environ.get("DATA_ROOT", str(DEFAULT_DATA_ROOT)) — 환경변수가 없으면 기본값 사용
    # "Config"를 문자열로 쓴 이유 — 클래스 정의가 끝나기 전에 자기 자신을 타입으로 참조할 때 전방 참조(forward reference) 로 씁니다
    @classmethod
    def from_env(cls) -> "Config":
        """환경변수에서 실행 설정을 읽어 Config를 만든다.

        LAW_API_OC는 국가법령정보센터 API 호출에 필요하므로 필수로 검사하고,
        DATA_ROOT는 지정되지 않으면 저장소의 data 디렉터리를 기본값으로 쓴다.
        """

        oc = os.environ.get("LAW_API_OC")

        if not oc:
            raise RuntimeError("LAW_API_OC 환경변수가 없습니다. pipelines/.env 를 설정하세요.")
        # os — 환경변수 읽기 (os.environ.get)
        data_root = Path(os.environ.get("DATA_ROOT", str(DEFAULT_DATA_ROOT)))
        return cls(data_root=data_root, oc=oc)
