"""Layer 2 — Machine Learning: RUL regression + anomaly detection.

Two regressors compete on the same engineered features:

* **baseline** — ``StandardScaler → Ridge``. Linear, fast, fully explainable;
  the number the candidate has to beat (and a good story for the review).
* **candidate** — ``HistGradientBoostingRegressor``. Captures the non-linear
  sensor drift a linear model cannot see, without needing a GPU or a deep net.
  It is the histogram-based (LightGBM-style) build of the same gradient-boosting
  family: an order of magnitude faster than the classic estimator, which is what
  makes an on-stage *retraining demo* possible.

Anomaly detection — ``IsolationForest`` fitted on the **healthy regime** only
(each engine's early life, where the RUL label sits at the clip). Its decision
function is converted to a 0–1 *abnormality percentile*: 0 looks like a healthy
reading, 1 is more abnormal than every healthy sample seen in training.

Evaluation metrics (quoted in the deck):

* **RMSE / MAE** — standard RUL error.
* **PHM score** — the classic run-to-failure scoring function; it punishes
  *late* predictions (claiming life remains when there is none) much harder
  than early ones, which is exactly the operational cost.
* **critical recall** — of the truly-critical validation rows (RUL ≤ 15), how
  many the model flags critical. This is the mild-imbalance answer: accuracy
  alone would hide it.

Data hygiene: the train/validation split is **by engine**, never by row —
putting one engine's cycles on both sides would leak the future into the past.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, IsolationForest
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import DEFAULT_WINDOW, RUL_CLIP, build_feature_frame, split_xy
from .ingest import load_subset

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"

#: Rows sitting at the RUL clip are an engine's early life → the healthy regime.
HEALTHY_RUL = RUL_CLIP

#: RUL at or below this counts as "critical" for the recall metric.
CRITICAL_RUL = 15


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
def phm_score(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    delta_early: float = 13.0,
    delta_late: float = 10.0,
) -> float:
    """Classic PHM04 scoring function (lower is better, 0 is perfect).

    ``exp(d/δ)`` style penalties for every engine, where ``d = ŷ − y``:

    * ``d < 0``  — predicted *less* life than reality (early call) uses the
      gentler ``δ = 13``;
    * ``d ≥ 0``  — predicted *more* life than reality (late call) uses the
      sharper ``δ = 10``, so late predictions grow much faster.
    """
    d = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    early = d < 0
    score = np.sum(np.exp(-d[early] / delta_early) - 1.0)
    score += np.sum(np.exp(d[~early] / delta_late) - 1.0)
    return float(score)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """RMSE, MAE, PHM score and critical recall for one prediction set."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true

    truly_critical = y_true <= CRITICAL_RUL
    n_critical = int(truly_critical.sum())
    if n_critical:
        caught = int((y_pred[truly_critical] <= CRITICAL_RUL).sum())
        critical_recall = caught / n_critical
    else:
        critical_recall = 0.0

    return {
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))),
        "phm_score": phm_score(y_true, y_pred),
        "critical_recall": float(critical_recall),
        "n_rows": int(len(y_true)),
    }


def abnormality_score(
    decisions: np.ndarray, healthy_decisions: np.ndarray
) -> np.ndarray:
    """Map IsolationForest decision values to a 0–1 abnormality percentile.

    The healthy training decisions form the reference distribution:
    a sample scoring 1.0 is more abnormal than *every* healthy reading.
    """
    healthy = np.sort(np.asarray(healthy_decisions, dtype=float))
    d = np.asarray(decisions, dtype=float)
    rank = np.searchsorted(healthy, d, side="right") / healthy.size
    return 1.0 - rank


# --------------------------------------------------------------------------
# training
# --------------------------------------------------------------------------
def train_models(
    frame: pd.DataFrame, random_state: int = 42, val_fraction: float = 0.2
) -> dict[str, Any]:
    """Fit baseline + candidate regressors and the anomaly detector.

    Returns the fitted objects, validation metrics and the validation engine
    ids (so tests can prove there is no engine overlap).
    """
    units = np.asarray(sorted(frame["unit_id"].unique()))
    rng = np.random.default_rng(random_state)
    n_val = max(1, int(round(units.size * val_fraction)))
    val_units = set(rng.choice(units, size=n_val, replace=False).tolist())
    train_units = set(units) - val_units

    val_mask = frame["unit_id"].isin(val_units)
    X_tr, y_tr = split_xy(frame[~val_mask])
    X_va, y_va = split_xy(frame[val_mask])

    baseline = Pipeline(
        [("scale", StandardScaler()), ("ridge", Ridge(alpha=1.0))]
    )
    candidate = HistGradientBoostingRegressor(
        max_iter=200,
        max_depth=4,
        learning_rate=0.1,
        early_stopping=False,
        random_state=random_state,
    )
    baseline.fit(X_tr, y_tr)
    candidate.fit(X_tr, y_tr)

    metrics = {
        "baseline": evaluate(y_va, baseline.predict(X_va)),
        "candidate": evaluate(y_va, candidate.predict(X_va)),
    }

    # Anomaly detector: healthy regime only (early life, RUL at the clip).
    healthy = frame[frame["rul"] == HEALTHY_RUL]
    if healthy.empty:  # degenerate/toy data — fall back to all rows
        healthy = frame
    X_h, _ = split_xy(healthy)
    anomaly = IsolationForest(
        n_estimators=200, contamination="auto", random_state=random_state
    )
    anomaly.fit(X_h)
    healthy_decisions = anomaly.decision_function(X_h)

    return {
        "baseline": baseline,
        "candidate": candidate,
        "anomaly": anomaly,
        "healthy_decisions": np.asarray(healthy_decisions, dtype=float),
        "metrics": metrics,
        "val_units": sorted(val_units),
        "train_units": sorted(train_units),
        "feature_columns": [c for c in frame.columns if c not in ("unit_id", "cycle", "rul")],
    }


def save_artifacts(
    result: dict[str, Any],
    model_dir: Path | str,
    subset: str,
    window: int,
    random_state: int,
) -> Path:
    """Persist fitted models + healthy reference + the production pointer."""
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    tag = subset.lower()

    joblib.dump(result["baseline"], model_dir / f"{tag}_baseline.joblib")
    joblib.dump(result["candidate"], model_dir / f"{tag}_candidate.joblib")
    joblib.dump(result["anomaly"], model_dir / f"{tag}_anomaly.joblib")
    np.save(model_dir / f"{tag}_healthy_decisions.npy", result["healthy_decisions"])

    metrics = result["metrics"]
    # Selection rule, decided up front: lowest validation RMSE wins (the
    # standard, stable RUL metric). PHM score is reported but not used to pick
    # the winner — over 20 validation engines its exponential tail is dominated
    # by ~4 rows, which would make model choice fragile. Ties → lower PHM.
    winner = min(
        ("baseline", "candidate"),
        key=lambda k: (metrics[k]["rmse"], metrics[k]["phm_score"]),
    )

    production = {
        "subset": subset,
        "window": window,
        "random_state": random_state,
        "production_model": winner,
        "selection_metric": "rmse",
        "metrics": metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": result["feature_columns"],
        "critical_rul": CRITICAL_RUL,
        "rul_clip": RUL_CLIP,
        "model_classes": {
            "baseline": "Pipeline(StandardScaler -> Ridge)",
            "candidate": "HistGradientBoostingRegressor",
            "anomaly": "IsolationForest",
        },
    }
    path = model_dir / "production.json"
    path.write_text(json.dumps(production, indent=2), encoding="utf-8")
    return path


def log_to_mlflow(
    result: dict[str, Any],
    production_path: Path,
    subset: str,
    window: int,
    random_state: int,
    tracking_uri: str | None = None,
) -> str:
    """Log params, metrics and artifacts to MLflow; returns the run id."""
    import mlflow

    model_dir = production_path.parent
    tag = subset.lower()

    uri = (
        tracking_uri
        or os.environ.get("MLFLOW_TRACKING_URI")
        # MLflow 3.x retires the plain file store → SQLite tracking DB (artifacts
        # still land in ./mlruns). Path must use forward slashes in the URL.
        or f"sqlite:///{(MODEL_DIR.parent / 'mlflow.db').as_posix()}"
    )
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("cmapss-rul")

    metrics = result["metrics"]
    flat = {
        f"{name}_{key}": value
        for name, values in metrics.items()
        for key, value in values.items()
    }

    with mlflow.start_run(run_name=f"{subset}-gb-ridge-iso") as run:
        mlflow.log_params(
            {
                "subset": subset,
                "window": window,
                "random_state": random_state,
                "max_iter": 200,
                "max_depth": 4,
                "learning_rate": 0.1,
                "ridge_alpha": 1.0,
                "rul_clip": RUL_CLIP,
                "critical_rul": CRITICAL_RUL,
                "n_val_engines": len(result["val_units"]),
                "n_train_engines": len(result["train_units"]),
            }
        )
        mlflow.log_metrics(flat)
        mlflow.log_artifact(str(production_path))
        # Version the fitted models as plain artifacts instead of the sklearn
        # flavor: flavor logging shells out for dependency resolution (network)
        # and skops blocks the histogram tree type. Our serving layer loads
        # these joblib files directly, so nothing is lost.
        for name in ("baseline", "candidate", "anomaly"):
            joblib_path = model_dir / f"{tag}_{name}.joblib"
            if joblib_path.exists():
                mlflow.log_artifact(str(joblib_path), artifact_path="models")
        healthy_path = Path(model_dir) / f"{tag}_healthy_decisions.npy"
        if healthy_path.exists():
            mlflow.log_artifact(str(healthy_path), artifact_path="models")
        return run.info.run_id


def train_subset(
    subset: str = "FD001",
    window: int = DEFAULT_WINDOW,
    random_state: int = 42,
    model_dir: Path | str = MODEL_DIR,
    tracking_uri: str | None = None,
    log_mlflow: bool = True,
) -> dict[str, Any]:
    """Full Layer-2 run for one subset: data → features → models → artifacts."""
    data = load_subset(subset)
    frame = build_feature_frame(data["train"], window=window)
    result = train_models(frame, random_state=random_state)
    production_path = save_artifacts(result, model_dir, subset, window, random_state)

    run_id = None
    if log_mlflow:
        run_id = log_to_mlflow(
            result, production_path, subset, window, random_state, tracking_uri
        )

    return {
        "subset": subset,
        "metrics": result["metrics"],
        "production_model": json.loads(production_path.read_text(encoding="utf-8"))[
            "production_model"
        ],
        "production_path": str(production_path),
        "run_id": run_id,
        "n_train_engines": len(result["train_units"]),
        "n_val_engines": len(result["val_units"]),
    }


if __name__ == "__main__":  # pragma: no cover - manual entry point
    summary = train_subset()
    print(json.dumps(summary, indent=2))
