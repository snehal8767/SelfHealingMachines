"""Tests for Layer 1 — cleaning, rolling features and RUL labels.

The toy frames keep these tests independent of the NASA download; the last
test exercises the real FD001 data when it is present.
"""
import numpy as np
import pandas as pd
import pytest

from pipeline.features import (
    DEFAULT_WINDOW,
    RUL_CLIP,
    add_rul_label,
    add_test_rul_label,
    add_rolling_features,
    build_feature_frame,
    clean,
    split_xy,
)
from pipeline.ingest import RAW_DIR, SENSORS, load_subset


def _toy_frame() -> pd.DataFrame:
    """Two engines whose sensor_1 rises by 1 each cycle (a clear trend)."""
    rows = []
    for unit, length in [(1, 10), (2, 6)]:
        for cycle in range(1, length + 1):
            row = {
                "unit_id": unit,
                "cycle": cycle,
                "setting_1": 0.0,
                "setting_2": 0.0,
                "setting_3": 100.0,
            }
            row.update({f"sensor_{i}": float(cycle) for i in range(1, 22)})
            rows.append(row)
    return pd.DataFrame(rows)


def test_rul_decreases_by_one_per_cycle():
    frame = add_rul_label(_toy_frame())
    engine = frame[frame["unit_id"] == 1].sort_values("cycle")
    assert engine["rul"].iloc[0] == 9
    assert engine["rul"].iloc[-1] == 0
    assert (engine["rul"].diff().iloc[1:] == -1).all()


def test_rul_is_clipped():
    frame = add_rul_label(_toy_frame(), clip=5)
    assert frame["rul"].max() == 5


def test_test_rul_label_uses_true_end_of_life():
    frame = add_test_rul_label(_toy_frame(), rul_values=[50, 30])
    engine = frame[frame["unit_id"] == 1].sort_values("cycle")
    # last observed cycle has the true RUL, earlier ones are larger
    assert engine["rul"].iloc[-1] == 50
    assert engine["rul"].iloc[0] == 59
    assert (engine["rul"].diff().iloc[1:] == -1).all()


def test_test_rul_label_rejects_unknown_engine():
    with pytest.raises(ValueError, match="No RUL given"):
        add_test_rul_label(_toy_frame(), rul_values=[50])  # engine 2 missing


def test_clean_fills_missing_values_inside_engine():
    frame = _toy_frame()
    frame.loc[3, "sensor_5"] = np.nan
    cleaned = clean(frame)
    assert not cleaned.isna().any().any()


def test_rolling_features_contain_no_nans():
    frame = add_rolling_features(clean(_toy_frame()), window=3)
    assert not frame.isna().any().any()
    for sensor in SENSORS[:3]:
        for suffix in ("roll_mean", "roll_std", "roll_trend"):
            assert f"{sensor}_{suffix}" in frame.columns


def test_trend_detects_increasing_sensor():
    frame = add_rolling_features(clean(_toy_frame()), window=3)
    # sensor_1 grows by exactly 1 each cycle → trend ≈ 1 once the window is warm.
    # Warm-up restarts per engine: first cycle has no diff, then the window fills.
    warm_up = 1 + (3 - 1)  # first cycle + window - 1
    for _, engine in frame.groupby("unit_id"):
        engine = engine.sort_values("cycle")
        assert (engine["sensor_1_roll_trend"].iloc[warm_up:] > 0.9).all()
        # warm-up rows are partial averages, never negative for an increasing sensor
        assert (engine["sensor_1_roll_trend"].iloc[1:warm_up] >= 0).all()


def test_split_xy_drops_identifiers():
    frame = build_feature_frame(_toy_frame(), window=DEFAULT_WINDOW)
    X, y = split_xy(frame)
    assert "unit_id" not in X.columns
    assert "cycle" not in X.columns
    assert "rul" not in X.columns
    assert len(X) == len(y) == 16


def test_split_xy_requires_label():
    with pytest.raises(ValueError, match="no 'rul' column"):
        split_xy(clean(_toy_frame()))


@pytest.mark.skipif(
    not (RAW_DIR / "train_FD001.txt").exists(), reason="NASA dataset not downloaded"
)
def test_real_fd001_end_to_end():
    data = load_subset("FD001")
    frame = build_feature_frame(data["train"], window=DEFAULT_WINDOW)
    assert frame.shape[0] == 20631
    assert not frame.isna().any().any()
    X, y = split_xy(frame)
    assert X.shape[1] == 3 + 21 + 21 * 3  # settings + sensors + 3 rolling per sensor
    assert y.max() == RUL_CLIP
    assert y.min() == 0
