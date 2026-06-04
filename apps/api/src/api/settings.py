import os
from dataclasses import dataclass, field

from rag.config import RagConfig

MLX_MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"


@dataclass
class Settings:
    rag: RagConfig = field(default_factory=RagConfig.from_env)
    mlx_model: str = MLX_MODEL
    max_tokens: int = 768
    temperature: float = 0.3

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            rag=RagConfig.from_env(),
            mlx_model=os.environ.get("MLX_MODEL", MLX_MODEL),
        )
