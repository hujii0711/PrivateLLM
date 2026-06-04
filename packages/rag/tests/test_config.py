from pathlib import Path

from rag.config import RagConfig, COLLECTION, MODEL_NAME


def test_constants_match_pipeline_contract():
    # Plan 1이 색인할 때 쓴 값과 동일해야 한다
    assert COLLECTION == "jeonse_deposit"
    assert MODEL_NAME == "BAAI/bge-m3"


def test_defaults(tmp_path):
    cfg = RagConfig(chroma_dir=tmp_path)
    assert cfg.collection == "jeonse_deposit"
    assert cfg.model_name == "BAAI/bge-m3"
    assert cfg.top_k == 6
    assert 0.0 < cfg.min_similarity < 1.0


def test_from_env_reads_chroma_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "c"))
    cfg = RagConfig.from_env()
    assert cfg.chroma_dir == tmp_path / "c"
