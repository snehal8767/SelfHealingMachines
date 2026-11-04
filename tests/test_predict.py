"""Tests for the inference layer — scoring the fleet with the production model.

Skips when either the NASA data or the trained artifacts are missing
(``python -m pipeline.train`` produces the artifacts).
"""
import numpy as np
import pytest

from pipeline.ingest import RAW_DIR, load_subset
from pipeline.predict import current_state, load_production, score_frame, score_test_set
from pipeline.train import MODEL_DIR

READY = (RAW_DIR / "train_FD001.txt").exists() and (MODEL_DIR / "production.json").exists()
pytestmark = pytest.mark.skipif(not READY, reason="needs NASA data + trained model")


def test_load_production_exposes_what_train_published():
    prod = load_production()
    assert prod["meta"]["subset"] == "FD001"
    assert prod["meta"]["production_model"] in ("baseline", "candidate")
    assert prod["meta"]["selection_metric"] == "rmse"
    assert len(prod["meta"]["feature_columns"]) == 87  # 3 settings + 21 sensors + 63 rolling
    assert prod["healthy_decisions"].size > 0


def test_score_test_set_follows_cmapss_protocol():
    result = score_test_set()
    state = result["current"]
    data = load_subset("FD001")
    n_engines = data["test"]["unit_id"].nunique()

    # the FD001 test split is a100-machine fleet with one official RUL label each
    assert n_engines == 100 == len(data["rul"])

    # one row per engine, at that engine's last observed cycle
    assert len(state) == n_engines
    assert state["unit_id"].is_unique

    last_cycle = data["test"].groupby("unit_id")["cycle"].max()
    for row in state.itertuples():
        assert row.cycle == last_cycle[row.unit_id]
        # true label attached to the current state must match the official file
        assert row.true_rul == data["rul"].iloc[row.unit_id - 1]

    metrics = result["metrics"]
    assert 0 < metrics["rmse"] < 40          # sane RUL error on the official test split
    assert 0 <= metrics["critical_recall"] <= 1
    assert metrics["n_rows"] == n_engines


def test_anomaly_scores_are_percentiles_between_zero_and_one():
    result = score_test_set()
    anomaly = result["rows"]["anomaly"].to_numpy()
    assert anomaly.min() >= 0.0
    assert anomaly.max() <= 1.0


def test_score_frame_rejects_missing_trained_features():
    from pipeline.features import build_feature_frame

    prod = load_production()
    frame = build_feature_frame(load_subset("FD001")["test"], with_rul=False)
    broken = frame.drop(columns=["sensor_5_roll_mean"])  # simulated schema drift
    with pytest.raises(ValueError, match="missing.*trained features"):
        score_frame(broken, prod)


def test_current_state_takes_the_latest_cycle():
    rows = score_test_set()["rows"]
    state = current_state(rows)
    latest = rows.groupby("unit_id")["cycle"].max()
    for row in state.itertuples():
        assert row.cycle == latest[row.unit_id]


def test_predictions_are_finite():
    rows = score_test_set()["rows"]
    assert np.isfinite(rows["predicted_rul"]).all()
    assert np.isfinite(rows["anomaly"]).all()
