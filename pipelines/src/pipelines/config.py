import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


@dataclass
class Config:
    data_root: Path
    oc: str

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw"

    @property
    def chunks_dir(self) -> Path:
        return self.data_root / "chunks"

    @property
    def chroma_dir(self) -> Path:
        return self.data_root / "chroma"

    def ensure_dirs(self) -> None:
        for d in (self.raw_dir, self.chunks_dir, self.chroma_dir):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        oc = os.environ.get("LAW_API_OC")
        if not oc:
            raise RuntimeError(
                "LAW_API_OC 환경변수가 없습니다. pipelines/.env 를 설정하세요."
            )
        data_root = Path(os.environ.get("DATA_ROOT", str(DEFAULT_DATA_ROOT)))
        return cls(data_root=data_root, oc=oc)
