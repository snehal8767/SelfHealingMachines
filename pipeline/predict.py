"""Layer 2 (inference) — score a fleet with the production model.

The serving side never re-trains: it loads exactly what ``pipeline/train.py``
published (``models/production.json`` → joblib models + healthy reference) and
applies it to fresh trajectories.

Protocol note: C-MAPSS is scored **per engine at its last observed cycle** —
that is what an operator would act on ("this machine, right now"). We therefore
expose both the full per-cycle series (for charts) and the current state
(one row per engine, used for triage and for benchmark metrics).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .features import DEFAULT_WINDOW, add_test_rul_label, build_feature_frame
from .ingest import load_subset
from .train import MODEL_DIR, abnormality_score, evaluate


def load_production(model_dir: Path | str = MODEL_DIR) -> dict[str, Any]:
    """Load the production pointer plus the models it names."""
    model_dir = Path(model_dir)
    meta = json.loads((model_dir / "production.json").read_text(encoding="utf-8"))
    tag = meta["subset"].lower()
    return {
        "meta": meta,
        "model": joblib.load(model_dir / f"{tag}_{meta['production_model']}.joblib"),
        "anomaly": joblib.load(model_dir / f"{tag}_anomaly.joblib"),
        "healthy_decisions": np.load(model_dir / f"{tag}_healthy_decisions.npy"),
        "window": int(meta.get("window", DEFAULT_WINDOW)),
        "model_dir": model_dir,
    }


def score_frame(frame: pd.DataFrame, production: dict[str, Any]) -> pd.DataFrame:
    """Predict RUL + abnormality for every row of a trajectory frame.

    Feature columns are reindexed to the training order recorded in
    ``production.json`` so a schema drift fails loudly instead of silently
    shuffling columns.
    """
    out = frame[["unit_id", "cycle"]].copy()
    drop = [c for c in ("unit_id", "cycle", "rul") if c in frame.columns]
    X = frame.drop(columns=drop)
    expected = production["meta"]["feature_columns"]
    missing = [c for c in expected if c not in X.columns]
    if missing:
        raise ValueError(f"Frame is missing {len(missing)} trained features, e.g. {missing[:3]}")
    X = X.reindex(columns=expected)  # enforce training order, keep extras out

    out["predicted_rul"] = production["model"].predict(X)
    out["anomaly"] = abnormality_score(
        production["anomaly"].decision_function(X),
        production["healthy_decisions"],
    )
    return out


def current_state(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per engine: its latest cycle (what an operator acts on)."""
    return (
        rows.sort_values(["unit_id", "cycle"])
        .groupby("unit_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )


def score_test_set(
    subset: str = "FD001", model_dir: Path | str = MODEL_DIR
) -> dict[str, Any]:
    """Score the official test split and report benchmark metrics.

    Returns the per-cycle rows, each engine's current state (with the *true*
    RUL attached for offline evaluation), and metrics computed at the current
    state — the C-MAPSS scoring protocol.
    """
    production = load_production(model_dir)
    data = load_subset(subset)

    frame = build_feature_frame(
        data["test"], window=production["window"], with_rul=False
    )
    rows = score_frame(frame, production)

    truth = add_test_rul_label(frame, data["rul"])
    rows["true_rul"] = truth["rul"].to_numpy()  # same row order

    state = current_state(rows)
    return {
        "subset": subset,
        "rows": rows,
        "current": state,
        "metrics": evaluate(state["true_rul"], state["predicted_rul"]),
        "meta": production["meta"],
    }


if __name__ == "__main__":  # pragma: no cover - manual entry point
    import json as _json

    result = score_test_set()
    print(_json.dumps(result["metrics"], indent=2))
