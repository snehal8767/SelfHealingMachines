"""Tests for Layer 2 — metrics, the engine-level split and the training run.

The metric tests are pure maths (no dataset needed); the full training test
skips itself when the NASA data has not been downloaded.
"""
import json

import numpy as np
import pytest

from pipeline.features import build_feature_frame
from pipeline.ingest import RAW_DIR, load_subset
from pipeline.train import (
    CRITICAL_RUL,
    abnormality_score,
    evaluate,
    phm_score,
    train_models,
    train_subset,
)

DATA_READY = (RAW_DIR / "train_FD001.txt").exists()


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
def test_perfect_prediction_scores_zero():
    y = np.array([100.0, 50.0, 0.0, 15.0])
    assert evaluate(y, y) == {
        "rmse": 0.0,
        "mae": 0.0,
        "phm_score": 0.0,
        "critical_recall": 1.0,
        "n_rows": 4,
    }


def test_phm_score_penalises_late_more_than_early():
    """Same magnitude error: claiming extra life must hurt more than cutting it short."""
    y = np.full(5, 50.0)
    early = phm_score(y, y - 20)   # predicted 30 when real is 50
    late = phm_score(y, y + 20)    # predicted 70 when real is 50
    assert late > early > 0


def test_phm_score_grows_with_error_size():
    y = np.full(5, 50.0)
    assert phm_score(y, y + 30) > phm_score(y, y + 10)


def test_evaluate_reports_rmse_and_mae():
    y_true = np.array([100.0, 50.0, 0.0])
    y_pred = np.array([110.0, 40.0, 10.0])
    m = evaluate(y_true, y_pred)
    assert m["rmse"] == pytest.approx(np.sqrt((100 + 100 + 100) / 3))
    assert m["mae"] == pytest.approx(10.0)


def test_critical_recall_only_counts_truly_critical_rows():
    y_true = np.array([100.0, 10.0, CRITICAL_RUL, 80.0])
    y_pred = np.array([95.0, 5.0, 40.0, 70.0])  # one critical row missed (flagged late)
    m = evaluate(y_true, y_pred)
    # 2 rows are truly critical (10 and 15); only the first was flagged ≤ 15
    assert m["critical_recall"] == pytest.approx(0.5)


def test_abnormality_score_percentile_semantics():
    healthy = np.array([0.0, 1.0, 2.0, 3.0])
    # far below the healthy range → fully abnormal; far above → fully normal
    assert abnormality_score(np.array([-10.0]), healthy)[0] == pytest.approx(1.0)
    assert abnormality_score(np.array([10.0]), healthy)[0] == pytest.approx(0.0)
    # right at the median of healthy data → roughly mid-range abnormality
    mid = abnormality_score(np.array([1.5]), healthy)[0]
    assert 0.4 <= mid <= 0.7


# --------------------------------------------------------------------------
# engine-level split
# --------------------------------------------------------------------------
def test_split_is_by_engine_never_by_row():
    frame = build_feature_frame(_toy())
    result = train_models(frame, random_state=42)
    overlap = set(result["val_units"]) & set(result["train_units"])
    assert overlap == set()
    assert set(result["val_units"]) | set(result["train_units"]) == {
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
    }


# --------------------------------------------------------------------------
# full training run (needs the NASA data)
# --------------------------------------------------------------------------
@pytest.mark.skipif(not DATA_READY, reason="NASA dataset not downloaded")
def test_train_subset_produces_metrics_and_artifacts(tmp_path):
    summary = train_subset(
        subset="FD001", model_dir=tmp_path, log_mlflow=False, random_state=42
    )

    metrics = summary["metrics"]
    for name in ("baseline", "candidate"):
        assert metrics[name]["rmse"] >= 0
        assert metrics[name]["phm_score"] >= 0
        assert 0 <= metrics[name]["critical_recall"] <= 1

    # Gradient boosting must beat Ridge on the primary metric (RMSE)
    assert metrics["candidate"]["rmse"] < metrics["baseline"]["rmse"]
    # ...and it must stay inside a valid RUL range (Ridge extrapolates below 0)
    # which is why it also gets the production pointer.

    # artifacts written and the pointer is valid JSON
    production = json.loads((tmp_path / "production.json").read_text(encoding="utf-8"))
    assert production["production_model"] in ("baseline", "candidate")
    assert production["selection_metric"] == "rmse"
    # the documented rule (lowest RMSE) picks the candidate on FD001
    assert production["production_model"] == "candidate"
    assert production["feature_columns"][0].startswith("setting_")
    assert summary["production_model"] == production["production_model"]
    for name in ("fd001_baseline", "fd001_candidate", "fd001_anomaly"):
        assert (tmp_path / f"{name}.joblib").exists()
    assert (tmp_path / "fd001_healthy_decisions.npy").exists()

    # every engine went to exactly one side of the split
    assert summary["n_train_engines"] + summary["n_val_engines"] == 100


def _toy() -> "object":
    """10 tiny engines so split/training logic can run without the dataset."""
    import pandas as pd

    rows = []
    for unit in range(1, 11):
        for cycle in range(1, 21):
            row = {
                "unit_id": unit,
                "cycle": cycle,
                "setting_1": 0.0,
                "setting_2": 0.0,
                "setting_3": 100.0,
            }
            # sensor drift grows with cycle + engine-specific offset
            row.update(
                {f"sensor_{i}": float(cycle) + unit * 0.1 for i in range(1, 22)}
            )
            rows.append(row)
    return pd.DataFrame(rows)
