from pathlib import Path

from pipelines.config import Config


def test_paths_are_under_data_root(tmp_path):
    cfg = Config(data_root=tmp_path, oc="testoc")
    assert cfg.raw_dir == tmp_path / "raw"
    assert cfg.chunks_dir == tmp_path / "chunks"
    assert cfg.chroma_dir == tmp_path / "chroma"


def test_ensure_dirs_creates_directories(tmp_path):
    cfg = Config(data_root=tmp_path, oc="testoc")
    cfg.ensure_dirs()
    assert cfg.raw_dir.is_dir()
    assert cfg.chunks_dir.is_dir()


def test_from_env_reads_oc(monkeypatch, tmp_path):
    monkeypatch.setenv("LAW_API_OC", "envoc")
    monkeypatch.setenv("DATA_ROOT", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.oc == "envoc"
    assert cfg.data_root == tmp_path


def test_from_env_missing_oc_raises(monkeypatch):
    monkeypatch.delenv("LAW_API_OC", raising=False)
    import pytest

    with pytest.raises(RuntimeError, match="LAW_API_OC"):
        Config.from_env()
