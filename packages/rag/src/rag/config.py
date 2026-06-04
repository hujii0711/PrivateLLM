import os
from dataclasses import dataclass
from pathlib import Path

# Plan 1(pipelines)이 색인 시 사용한 값과 동일해야 한다.
COLLECTION = "jeonse_deposit"
MODEL_NAME = "BAAI/bge-m3"

# data/chroma 기본 위치(레포 루트 기준). config.py: packages/rag/src/rag/config.py
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CHROMA = _REPO_ROOT / "data" / "chroma"


@dataclass
class RagConfig:
    chroma_dir: Path = _DEFAULT_CHROMA
    collection: str = COLLECTION
    model_name: str = MODEL_NAME
    top_k: int = 6
    min_similarity: float = 0.35   # cosine 유사도 하한(이하면 grounding 약함으로 처리)

    @classmethod
    def from_env(cls) -> "RagConfig":
        chroma = os.environ.get("CHROMA_DIR")
        return cls(chroma_dir=Path(chroma) if chroma else _DEFAULT_CHROMA)
