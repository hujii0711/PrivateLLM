import json

from ftdata.builder import split_train_valid, to_chat_example, write_jsonl
from rag.types import Retrieved


def _hit(ref):
    return Retrieved(id="i", text=f"근거 {ref}", similarity=0.7, source_type="법령",
                     title=f"주택임대차보호법 {ref}", ref=ref, url="u", date="2023")


def test_to_chat_example_has_system_user_assistant():
    ex = to_chat_example(
        "보증금?",
        [_hit("제3조의2")],
        "① ② ③ 우선변제[1]. ※ ... 법률 자문이 아닙니다."
    )
    roles = [m["role"] for m in ex["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert "근거" in ex["messages"][1]["content"]          # user에 근거 블록
    assert "보증금?" in ex["messages"][1]["content"]        # 질문 포함
    assert ex["messages"][2]["content"].startswith("①")    # assistant = 답변


def test_split_train_valid_deterministic():
    examples = [{"messages": [{"role": "user", "content": str(i)}]} for i in range(10)]
    train, valid = split_train_valid(examples, valid_every=5)
    # 5번째, 10번째(1-indexed)가 valid
    assert len(valid) == 2 and len(train) == 8
    assert valid[0]["messages"][0]["content"] == "4"      # index 4 (5th)


def test_write_jsonl_roundtrip(tmp_path):
    rows = [{"messages": [{"role": "user", "content": "a"}]},
            {"messages": [{"role": "user", "content": "b"}]}]
    p = tmp_path / "train.jsonl"
    write_jsonl(p, rows)
    back = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()]
    assert back == rows
