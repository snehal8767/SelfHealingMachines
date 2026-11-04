"""Tests for the persisted processed dataset (validation + round-trip + hashes).

Toy frames keep the validation rules independent of the NASA download; the
FD001 tests run only when the raw data is present.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from pipeline.dataset import build_processed, load_processed, validate_frame
from pipeline.features import RUL_CLIP
from pipeline.ingest import RAW_DIR, load_subset

DATA_READY = (RAW_DIR / "train_FD001.txt").exists()


def _toy() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "unit_id": [1, 1, 2],
            "cycle": [1, 2, 1],
            "sensor_1": [1.0, 2.0, 3.0],
            "rul": [1, 0, 5],
        }
    )


def test_validate_accepts_clean_frame():
    validate_frame(_toy(), require_rul=True)


def test_validate_rejects_duplicate_keys():
    with pytest.raises(ValueError, match="duplicate"):
        validate_frame(_toy().iloc[[0, 0, 2]], require_rul=True)


def test_validate_rejects_nan():
    frame = _toy()
    frame.loc[0, "sensor_1"] = np.nan
    with pytest.raises(ValueError, match="NaN/inf"):
        validate_frame(frame, require_rul=True)


def test_validate_rejects_infinite():
    frame = _toy()
    frame.loc[1, "sensor_1"] = np.inf
    with pytest.raises(ValueError, match="NaN/inf"):
        validate_frame(frame, require_rul=True)


def test_validate_rejects_missing_label():
    with pytest.raises(ValueError, match="required"):
        validate_frame(_toy().drop(columns=["rul"]), require_rul=True)


def test_validate_rejects_negative_rul():
    frame = _toy()
    frame.loc[0, "rul"] = -1
    with pytest.raises(ValueError, match="negative RUL"):
        validate_frame(frame, require_rul=True)


def test_validate_rejects_non_numeric_columns():
    frame = _toy()
    frame["note"] = "ok"
    with pytest.raises(ValueError, match="non-numeric"):
        validate_frame(frame, require_rul=True)


def test_validate_rejects_bad_cycle():
    frame = _toy()
    frame.loc[0, "cycle"] = 0
    with pytest.raises(ValueError, match="cycle must be"):
        validate_frame(frame, require_rul=True)


@pytest.mark.skipif(not DATA_READY, reason="NASA dataset not downloaded")
def test_build_fd001_roundtrip(tmp_path):
    manifest = build_processed("FD001", out_dir=tmp_path)

    train = load_processed("FD001", "train", out_dir=tmp_path)
    test = load_processed("FD001", "test", out_dir=tmp_path)
    truth = load_processed("FD001", "test_rul", out_dir=tmp_path)

    assert train.shape[0] == 20631
    assert "rul" in train.columns
    assert "rul" not in test.columns, "test features must not ship labels"
    assert "rul" in truth.columns
    assert len(truth) == 100

    assert train["rul"].min() == 0
    assert train["rul"].max() == RUL_CLIP
    assert not train.isna().any().any()
    assert not test.isna().any().any()

    assert len(manifest["feature_columns"]) == 87
    assert manifest["n_train_engines"] == 100
    assert manifest["n_test_engines"] == 100

    on_disk = json.loads((tmp_path / "fd001_manifest.json").read_text(encoding="utf-8"))
    assert on_disk["subset"] == "FD001"


@pytest.mark.skipif(not DATA_READY, reason="NASA dataset not downloaded")
def test_truth_matches_official_rul_file(tmp_path):
    build_processed("FD001", out_dir=tmp_path)
    truth = load_processed("FD001", "test_rul", out_dir=tmp_path)
    official = load_subset("FD001")["rul"]

    assert truth["rul"].tolist() == official.tolist()
    assert truth["unit_id"].tolist() == list(range(1, len(official) + 1))


@pytest.mark.skipif(not DATA_READY, reason="NASA dataset not downloaded")
def test_build_is_deterministic(tmp_path):
    first = build_processed("FD001", out_dir=tmp_path / "a")
    second = build_processed("FD001", out_dir=tmp_path / "b")

    for name in ("train", "test", "test_rul"):
        assert first["files"][name]["sha256"] == second["files"][name]["sha256"], (
            f"{name} differs between identical runs"
        )
