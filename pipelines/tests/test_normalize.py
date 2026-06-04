from pipelines.clean.normalize import normalize_text


def test_collapses_whitespace():
    assert normalize_text("가  나\t다") == "가 나 다"


def test_strips_and_normalizes_newlines():
    assert normalize_text("\n\n가\n\n\n나\n") == "가\n나"


def test_removes_soft_hyphen_and_nbsp():
    assert normalize_text("가­나 다") == "가나 다"


def test_empty_stays_empty():
    assert normalize_text("   ") == ""
