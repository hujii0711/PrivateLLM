"""
train.py — MLX LoRA 학습 명령어 빌더 모듈

【이 파일이 하는 일】
`mlx_lm.lora` 명령어를 파이썬 리스트(list[str])로 조립합니다.
실제 학습 실행은 이 모듈을 호출하는 쪽(CLI 또는 subprocess)에서 담당합니다.

【설계 포인트: 명령어 빌더 패턴】
학습 명령을 직접 문자열로 만들면 인자 추가/수정이 번거롭고 오타가 나기 쉽습니다.
build_lora_command() 는 파이썬 함수로 각 인자를 명시적으로 받아
list[str] 로 반환합니다. 이 리스트를 subprocess.run() 에 전달하면 실행됩니다.

    cmd = build_lora_command(model="mlx-community/Qwen2.5-7B-Instruct-4bit", ...)
    subprocess.run(cmd)  # 실제 학습 실행

【LoRA (Low-Rank Adaptation) 란?】
전체 모델 가중치(수십억 개 파라미터)를 재학습하는 대신,
소규모 어댑터 레이어(수백만 개)만 추가 학습하는 파인튜닝 기법입니다.

장점:
  - 메모리 사용량 대폭 감소 (7B 모델을 M3 Mac 에서도 학습 가능)
  - 학습 속도 빠름
  - 원본 모델 가중치 보존 (어댑터만 저장/교체 가능)

【QLoRA (Quantized LoRA) 란?】
4-bit 양자화된 모델에 LoRA 를 적용하는 방식입니다.
이 프로젝트는 4bit 양자화 모델(Qwen2.5-7B-Instruct-4bit)을 사용하므로
사실상 QLoRA 를 수행합니다.

【num_layers 파라미터】
LoRA 어댑터를 적용할 트랜스포머 레이어의 수입니다.
레이어 수가 많을수록 학습 용량이 크지만 메모리를 더 사용합니다.
7B 모델의 경우 전체 32개 레이어 중 8개(기본값)에만 적용합니다.
"""


def build_lora_command(
    *,                              # 모든 인자를 키워드 인자로 강제
    model: str,                     # 학습 기반이 될 모델 이름 (Hugging Face 경로)
    data_dir: str,                  # 학습 데이터 디렉터리 (train.jsonl, valid.jsonl 포함)
    adapter_dir: str,               # 학습된 어댑터를 저장할 디렉터리
    iters: int = 300,               # 학습 반복 횟수 (iteration 수)
    batch_size: int = 1,            # 배치 크기 (메모리가 작으면 1로 설정)
    num_layers: int = 8,            # LoRA 어댑터를 적용할 트랜스포머 레이어 수
    learning_rate: float = 1e-5,    # 학습률 (가중치 업데이트 크기, 1e-5 = 0.00001)
) -> list[str]:
    """mlx_lm.lora LoRA 학습 명령을 list[str] 형태로 반환합니다.

    반환된 리스트는 subprocess.run() 에 직접 전달할 수 있습니다.

    Args:
        model        : 베이스 모델 경로 (예: "mlx-community/Qwen2.5-7B-Instruct-4bit")
        data_dir     : train.jsonl, valid.jsonl 이 있는 디렉터리 경로
        adapter_dir  : 학습 완료 후 어댑터 가중치를 저장할 경로
        iters        : 학습 스텝 수 (300 이면 300번 가중치 업데이트)
        batch_size   : 한 번에 처리할 샘플 수 (Mac M 시리즈 메모리가 제한적이므로 1 권장)
        num_layers   : LoRA 적용 레이어 수 (더 많을수록 학습 효과↑, 메모리↑)
        learning_rate: 학습률 (너무 크면 발산, 너무 작으면 학습 안 됨)

    Returns:
        subprocess.run() 에 전달할 명령어 토큰 리스트

    사용 예:
        cmd = build_lora_command(
            model="mlx-community/Qwen2.5-7B-Instruct-4bit",
            data_dir="./data/ft",
            adapter_dir="./data/adapters/qlora",
        )
        # cmd = ["python", "-m", "mlx_lm.lora", "--model", "...", ...]
        import subprocess
        subprocess.run(cmd, check=True)
    """
    return [
        "python", "-m", "mlx_lm.lora",   # mlx-lm 패키지의 LoRA 학습 모듈 실행
        "--model", model,                  # 학습할 베이스 모델
        "--train",                         # 학습 모드 플래그 (추론이 아닌 학습)
        "--data", str(data_dir),           # 데이터 디렉터리 경로
        "--adapter-path", str(adapter_dir),  # 어댑터 저장 경로
        "--iters", str(iters),             # 학습 반복 횟수
        "--batch-size", str(batch_size),   # 미니배치 크기
        "--num-layers", str(num_layers),   # LoRA 적용 레이어 수
        "--learning-rate", str(learning_rate),  # 학습률
    ]
