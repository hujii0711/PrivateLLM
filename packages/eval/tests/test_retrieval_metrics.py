from eval.retrieval_metrics import ref_hit, recall_at_k


def test_ref_hit_true_when_expected_ref_retrieved():
    assert ref_hit(retrieved_refs=["제3조의2", "제4조"], expected_refs=["제3조의2"]) is True


def test_ref_hit_false_when_none_retrieved():
    assert ref_hit(retrieved_refs=["제4조"], expected_refs=["제3조의2"]) is False


def test_ref_hit_true_if_any_expected_present():
    # 기대 ref 중 하나라도 검색되면 hit
    assert ref_hit(retrieved_refs=["제3조의3"], expected_refs=["제3조의2", "제3조의3"]) is True


def test_ref_hit_with_no_expected_refs_is_true():
    # 기대 조문이 없는 항목은 검색 평가에서 제외(hit=True로 무시)
    assert ref_hit(retrieved_refs=["제4조"], expected_refs=[]) is True


def test_recall_at_k_is_mean_hit_rate():
    # 3개 항목 중 2개 hit → 2/3
    per_item = [True, False, True]
    assert recall_at_k(per_item) == 2 / 3
