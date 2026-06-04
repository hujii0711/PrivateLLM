import pytest

from api.llm import FakeLLM


def test_fake_llm_streams_scripted_tokens():
    llm = FakeLLM(["안녕", "하세", "요"])
    msgs = [{"role": "user", "content": "x"}]
    assert list(llm.stream(msgs)) == ["안녕", "하세", "요"]


def test_fake_llm_full_text_helper():
    llm = FakeLLM(["a", "b", "c"])
    assert "".join(llm.stream([{"role": "user", "content": "x"}])) == "abc"


@pytest.mark.slow
def test_mlx_llm_generates_korean():
    from api.llm import MlxLLM
    llm = MlxLLM()  # 실제 모델 로딩(~4.3GB, 최초 1회 다운로드)
    msgs = [{"role": "system", "content": "한국어로 한 문장 답하세요."},
            {"role": "user", "content": "보증금 반환이 뭔가요?"}]
    text = "".join(llm.stream(msgs, max_tokens=64))
    assert text.strip()
    assert any("가" <= ch <= "힣" for ch in text)   # 한글 포함
