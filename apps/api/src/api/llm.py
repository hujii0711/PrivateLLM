"""
llm.py — LLM(대규모 언어 모델) 추상화 및 구현 모듈

【이 파일이 하는 일】
1. LLM Protocol  : "어떤 LLM이든 stream() 메서드를 구현하면 된다"는 인터페이스(계약)를 정의합니다.
2. FakeLLM       : 실제 모델 없이 테스트할 때 쓰는 가짜 LLM입니다.
3. MlxLLM        : Apple Silicon(M1/M2/M3) 최적화 프레임워크인 MLX를 사용해
                   로컬에서 Qwen2.5-7B 모델을 실행하는 실제 LLM 구현체입니다.

【스트리밍(Streaming)이란?】
LLM이 응답을 한꺼번에 보내지 않고, 생성된 단어(토큰)를 즉시즉시 클라이언트에
전달하는 방식입니다. ChatGPT 에서 글자가 하나씩 나타나는 것과 같은 원리입니다.

【Protocol이란?】
파이썬의 덕 타이핑(Duck Typing)을 공식화한 것입니다.
"stream() 메서드를 가진 객체라면 모두 LLM으로 취급한다"는 규칙을 명시합니다.
이 덕분에 FakeLLM, MlxLLM 등 어떤 구현체도 같은 방식으로 교체해서 쓸 수 있습니다.
"""

from collections.abc import Iterator  # 제너레이터·이터레이터의 타입 힌트에 사용
from typing import Protocol  # 인터페이스(추상 계약)를 정의하는 도구

from .settings import MLX_MODEL  # 기본 모델 이름 상수 import (상대 경로 import)


# ══════════════════════════════════════════════════════════════
# LLM Protocol — 인터페이스(계약) 정의
# ══════════════════════════════════════════════════════════════
class LLM(Protocol):
    """모든 LLM 구현체가 반드시 지켜야 하는 인터페이스.

    파이썬의 Protocol 은 Java 의 Interface, TypeScript 의 interface 와 유사합니다.
    "명시적으로 상속하지 않아도, stream() 메서드 시그니처가 맞으면 LLM으로 인정"합니다.

    사용 예:
        def run(llm: LLM):   # LLM Protocol을 만족하는 객체면 모두 OK
            for token in llm.stream(messages):
                print(token)
    """

    def stream(
        self,
        messages: list[dict],  # OpenAI 형식의 대화 메시지 목록
        *,  # * 이후 인자는 반드시 키워드 인자로 전달해야 합니다
        max_tokens: int = 768,  # 생성할 최대 토큰(단어 조각) 수
        temperature: float = 0.3,  # 생성 무작위성 (0~1)
    ) -> Iterator[str]:  # 문자열 토큰을 하나씩 yield하는 이터레이터 반환
        ...  # Protocol 에서는 구현 대신 ... 으로 "구현 필요"를 표시합니다


# ══════════════════════════════════════════════════════════════
# FakeLLM — 테스트 전용 가짜 LLM
# ══════════════════════════════════════════════════════════════
class FakeLLM:
    """실제 모델 없이 단위 테스트(Unit Test)에 사용하는 가짜 LLM.

    초기화 시 토큰 목록을 미리 넣어두면, stream() 호출 시 그 토큰들을 순서대로 반환합니다.
    덕분에 무거운 ML 모델을 로드하지 않고도 파이프라인 로직을 빠르게 테스트할 수 있습니다.

    사용 예:
        fake = FakeLLM(["안녕", "하세요", "!"])
        for tok in fake.stream([]):
            print(tok)   # "안녕", "하세요", "!" 순서로 출력
    """

    def __init__(self, tokens: list[str]):
        """
        Args:
            tokens: stream() 호출 시 순서대로 반환할 문자열(토큰) 목록
        """
        # 인스턴스 변수에 토큰 목록을 저장합니다.
        # 앞에 _ 를 붙이는 것은 "외부에서 직접 접근하지 말 것"을 나타내는 관례입니다.
        self._tokens = tokens

    def stream(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 768,
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """미리 저장된 토큰들을 하나씩 yield합니다.

        messages, max_tokens, temperature 인자는 LLM Protocol 을 맞추기 위해
        선언되어 있지만, FakeLLM 에서는 실제로 사용하지 않습니다.

        yield from : iterable(반복 가능 객체)의 요소를 하나씩 yield하는 파이썬 문법
        """
        yield from self._tokens  # self._tokens 리스트의 각 요소를 순서대로 반환


# ══════════════════════════════════════════════════════════════
# MlxLLM — 실제 로컬 LLM 구현체
# ══════════════════════════════════════════════════════════════
class MlxLLM:
    """Apple Silicon 전용 MLX 프레임워크로 Qwen2.5-7B 모델을 실행하는 LLM.

    【MLX 란?】
    Apple 이 M 시리즈 칩(M1/M2/M3) 의 Neural Engine 과 통합 메모리(Unified Memory)를
    최대한 활용하도록 만든 머신러닝 프레임워크입니다.
    GPU와 CPU가 메모리를 공유해 대형 모델도 Mac 에서 빠르게 실행할 수 있습니다.

    【LoRA (Low-Rank Adaptation) 란?】
    전체 모델 가중치를 재학습하지 않고, 소규모 어댑터 레이어만 추가 학습하는 기법입니다.
    특정 도메인(예: 주택임대차 법률)에 특화시킬 때 사용합니다.
    adapter_path 를 지정하면 LoRA 어댑터가 모델에 자동으로 적용됩니다.
    """

    def __init__(
        self,
        model_name: str = MLX_MODEL,  # 로드할 모델 이름 (Hugging Face 경로)
        adapter_path: str | None = None,  # LoRA 어댑터 경로 (없으면 기본 모델만 사용)
    ):
        """모델과 토크나이저를 메모리에 로드합니다.

        【지연 import (Lazy Import) 패턴】
        mlx_lm import 를 함수 안에서 수행하는 이유:
          - mlx_lm 은 Apple Silicon 이 없는 환경(CI, 리눅스 서버 등)에서 설치가 안 될 수 있습니다.
          - 모듈 최상단에 import 하면 mlx_lm 없이는 파일 자체를 불러올 수 없게 됩니다.
          - 함수 내부에서 import 하면 MlxLLM 인스턴스를 실제로 만들 때만 mlx_lm 을 요구합니다.
          - 따라서 FakeLLM 만 사용하는 테스트 환경에서는 mlx_lm 이 없어도 괜찮습니다.

        Args:
            model_name  : 다운로드/캐시된 모델의 Hugging Face 식별자
            adapter_path: LoRA 어댑터 가중치가 저장된 디렉터리 경로 (선택)
        """
        from mlx_lm import load  # mlx-lm 패키지에서 모델 로드 함수 import

        # load() 는 (model, tokenizer) 튜플을 반환합니다.
        # adapter_path 를 지정하면 LoRA 어댑터가 자동으로 적용됩니다.
        loaded = load(model_name, adapter_path=adapter_path)

        self._model = loaded[0]  # 실제 신경망 모델 (가중치 포함), 로드된 실제 신경망 모델 객체 (가중치 포함)
        self._tokenizer = loaded[1]  # 텍스트 ↔ 토큰 ID 변환 담당, 텍스트와 토큰 ID 간의 변환을 담당하는 토크나이저 객체

    def stream(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 768,
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """채팅 메시지를 받아 LLM 응답을 스트리밍으로 생성합니다.

        처리 흐름:
          1. 메시지 목록 → 채팅 템플릿 적용 → 단일 프롬프트 문자열 생성
          2. 샘플러(Sampler) 설정 : temperature 를 기반으로 토큰 선택 전략 결정
          3. stream_generate() 로 토큰을 하나씩 생성하며 yield

        Args:
            messages   : [{"role": "user", "content": "질문"}, ...] 형식의 대화 목록
            max_tokens : 최대 생성 토큰 수 (넘어가면 생성 중단)
            temperature: 0에 가까울수록 결정론적(항상 같은 답), 1에 가까울수록 무작위

        Yields:
            str: 생성된 텍스트 조각(토큰). 모든 조각을 이으면 전체 답변이 됩니다.
        """
        from mlx_lm import stream_generate  # 스트리밍 생성 함수
        from mlx_lm.sample_utils import make_sampler  # 샘플링 전략 생성 도우미

        # apply_chat_template : 메시지 목록을 모델이 이해하는 형식으로 변환합니다.
        #   add_generation_prompt=True : 모델이 답변을 시작하도록 특수 토큰을 추가합니다.
        #   tokenize=False             : 토큰 ID 배열이 아닌 문자열로 반환합니다.
        prompt = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )

        # make_sampler(temp=temperature) : 온도(temperature)에 따른 샘플링 전략 객체 생성
        #   temperature=0.0 → 항상 확률이 가장 높은 토큰 선택 (greedy decoding)
        #   temperature=1.0 → 확률 분포에서 무작위 샘플링
        sampler = make_sampler(temp=temperature)

        # stream_generate : 프롬프트에 이어지는 텍스트를 한 토큰씩 생성합니다.
        # 각 반복마다 resp 객체가 반환되며, resp.text 에 생성된 텍스트 조각이 담겨 있습니다.
        for resp in stream_generate(
            self._model,
            self._tokenizer,
            prompt,
            max_tokens=max_tokens,
            sampler=sampler,
        ):
            yield resp.text  # 생성된 텍스트 조각을 즉시 호출자에게 전달
