from api.schemas import ChatRequest, SourceOut


def test_chat_request_requires_message():
    req = ChatRequest(message="보증금 못 받았어요")
    assert req.message == "보증금 못 받았어요"


def test_source_out_shape():
    s = SourceOut(n=1, title="주택임대차보호법 제3조의2", ref="제3조의2",
                  url="https://law/1", source_type="법령")
    assert s.n == 1 and s.source_type == "법령"
