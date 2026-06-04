"""LLM 추상화 + MLX Qwen 구현. FakeLLM으로 모델 없이 테스트 가능."""
from typing import Iterator, Protocol

from .settings import MLX_MODEL


class LLM(Protocol):
    def stream(self, messages: list[dict], *, max_tokens: int = 768,
               temperature: float = 0.3) -> Iterator[str]:
        ...


class FakeLLM:
    """미리 정해진 토큰을 차례로 내보내는 테스트용 LLM."""
    def __init__(self, tokens: list[str]):
        self._tokens = tokens

    def stream(self, messages: list[dict], *, max_tokens: int = 768,
               temperature: float = 0.3) -> Iterator[str]:
        for t in self._tokens:
            yield t


class MlxLLM:
    """mlx-lm 기반 Qwen2.5-7B-Instruct-4bit 스트리밍 추론. LoRA 어댑터 적용 가능."""
    def __init__(self, model_name: str = MLX_MODEL, adapter_path: str | None = None):
        from mlx_lm import load
        self._model, self._tokenizer = load(model_name, adapter_path=adapter_path)

    def stream(self, messages: list[dict], *, max_tokens: int = 768,
               temperature: float = 0.3) -> Iterator[str]:
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler

        prompt = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False)
        sampler = make_sampler(temp=temperature)
        for resp in stream_generate(self._model, self._tokenizer, prompt,
                                    max_tokens=max_tokens, sampler=sampler):
            yield resp.text
