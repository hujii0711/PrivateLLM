"""mlx_lm.lora QLoRA 학습 명령 빌더(라이브 실행은 호출 측에서 subprocess)."""


def build_lora_command(*, model: str, data_dir: str, adapter_dir: str,
                       iters: int = 300, batch_size: int = 1,
                       num_layers: int = 8, learning_rate: float = 1e-5) -> list[str]:
    """mlx-lm 0.31.3 기준 LoRA 학습 명령(list[str])."""
    return [
        "python", "-m", "mlx_lm.lora",
        "--model", model,
        "--train",
        "--data", str(data_dir),
        "--adapter-path", str(adapter_dir),
        "--iters", str(iters),
        "--batch-size", str(batch_size),
        "--num-layers", str(num_layers),
        "--learning-rate", str(learning_rate),
    ]
