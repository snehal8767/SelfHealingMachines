"""Tests for Layer 1 — data ingestion from the NASA C-MAPSS files.

These tests are skipped automatically when the dataset has not been
downloaded yet (see data/README.md).
"""
from pathlib import Path

import pytest

from pipeline.ingest import COLUMNS, RAW_DIR, load_subset

DATA_READY = (RAW_DIR / "train_FD001.txt").exists()
pytestmark = pytest.mark.skipif(not DATA_READY, reason="NASA dataset not downloaded")


def test_load_fd001_shapes():
    data = load_subset("FD001")
    assert data["train"].shape == (20631, 26)
    assert list(data["train"].columns) == COLUMNS
    assert data["test"]["unit_id"].nunique() == len(data["rul"])
    assert len(data["rul"]) > 0


def test_no_missing_values_and_valid_cycles():
    data = load_subset("FD001")
    for name in ("train", "test"):
        frame = data[name]
        assert not frame.isna().any().any(), f"{name} contains NaN"
        assert (frame["cycle"] >= 1).all()
        assert (frame["unit_id"] >= 1).all()


def test_rul_labels_are_positive_integers():
    data = load_subset("FD001")
    assert data["rul"].dtype.kind == "i"
    assert (data["rul"] >= 0).all()


def test_unknown_subset_raises():
    with pytest.raises(ValueError, match="Unknown subset"):
        load_subset("FD009")


def test_missing_file_raises_with_hint(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="data/README.md"):
        load_subset("FD001", raw_dir=tmp_path)
