import inspect

from api.llm import MlxLLM


def test_mlxllm_init_accepts_adapter_path():
    params = inspect.signature(MlxLLM.__init__).parameters
    assert "adapter_path" in params
    assert params["adapter_path"].default is None   # 기본은 어댑터 없음(하위호환)
