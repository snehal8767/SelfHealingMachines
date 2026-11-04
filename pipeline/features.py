"""Layer 1 — cleaning, rolling-window features and RUL labels.

Design decisions (documented for the review deck):

* **Missing values** — forward-filled *within* an engine (a sensor value cannot
  come from another machine), then any residual NaN falls back to 0.
* **Basic noise** — the rolling mean over the last W cycles doubles as light
  smoothing; we keep the raw sensor column alongside it so nothing is lost.
* **Rolling features** — per engine, per sensor:
    ``*_roll_mean``  level over the window (averages, as the brief asks)
    ``*_roll_std``   volatility (a rising std often precedes failure)
    ``*_roll_trend`` mean of the first difference ≈ slope per cycle (trends)
  ``min_periods=1`` keeps early cycles usable, so no NaNs reach the model.
* **RUL label** — ``last_cycle(engine) - cycle``, clipped at 125 (the standard
  C-MAPSS cap) so the model is not forced to extrapolate a useless tail.
* **Excluded from features** — ``unit_id`` and ``cycle``: the raw cycle number
  would let the model memorise engine age instead of reading sensor health.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .ingest import SENSORS, SETTINGS

RUL_CLIP = 125
DEFAULT_WINDOW = 5

RAW_FEATURE_COLS = [*SETTINGS, *SENSORS]


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by engine/cycle and fill missing values inside each engine."""
    out = df.sort_values(["unit_id", "cycle"]).reset_index(drop=True).copy()
    numeric = out.select_dtypes(include="number").columns
    out[numeric] = out.groupby("unit_id")[numeric].ffill().bfill()
    out[numeric] = out[numeric].fillna(0.0)  # engines that are NaN from the start
    return out


def add_rul_label(df: pd.DataFrame, clip: int = RUL_CLIP) -> pd.DataFrame:
    """Training data: RUL = last observed cycle of that engine - current cycle."""
    out = df.copy()
    last_cycle = out.groupby("unit_id")["cycle"].transform("max")
    out["rul"] = (last_cycle - out["cycle"]).clip(upper=clip).astype("int64")
    return out


def add_test_rul_label(
    df: pd.DataFrame, rul_values: pd.Series | np.ndarray | list
) -> pd.DataFrame:
    """Test data: engines are truncated, so true RUL is given per engine.

    ``rul_values[i]`` is the true remaining life of test engine ``i + 1``
    at its **last observed cycle**; earlier cycles add back the cycles already run.

    The label is stored **unclipped on purpose** — this is ground truth used for
    scoring against the official C-MAPSS protocol. *Training* labels are the
    clipped ones from :func:`add_rul_label`; clipping truth here would flatter
    the metrics on engines with more than 125 cycles left.
    """
    out = df.copy()
    values = np.asarray(rul_values, dtype=float).ravel()
    mapping = {i + 1: v for i, v in enumerate(values)}
    unknown = set(out["unit_id"].unique()) - set(mapping)
    if unknown:
        raise ValueError(f"No RUL given for test engines: {sorted(unknown)}")

    end_of_life = out["unit_id"].map(mapping).astype(float)
    last_cycle = out.groupby("unit_id")["cycle"].transform("max")
    # earlier cycles have MORE life left: rul grows as we move back in time
    out["rul"] = (end_of_life + (last_cycle - out["cycle"])).astype("int64")
    return out


def add_rolling_features(df: pd.DataFrame, window: int = DEFAULT_WINDOW) -> pd.DataFrame:
    """Add per-engine rolling mean / std / trend for every sensor."""
    if window < 1:
        raise ValueError("window must be >= 1")

    out = df.sort_values(["unit_id", "cycle"]).reset_index(drop=True).copy()
    grouped = out.groupby("unit_id")[SENSORS]

    means = grouped.transform(lambda s: s.rolling(window, min_periods=1).mean())
    means.columns = [f"{c}_roll_mean" for c in SENSORS]

    stds = grouped.transform(lambda s: s.rolling(window, min_periods=1).std())
    stds.columns = [f"{c}_roll_std" for c in SENSORS]
    stds = stds.fillna(0.0)  # std of a single sample is undefined

    deltas = grouped.diff().fillna(0.0)  # per-cycle change
    trends = deltas.groupby(out["unit_id"]).transform(
        lambda s: s.rolling(window, min_periods=1).mean()
    )
    trends.columns = [f"{c}_roll_trend" for c in SENSORS]

    return pd.concat([out, means, stds, trends], axis=1)


def build_feature_frame(
    df: pd.DataFrame, window: int = DEFAULT_WINDOW, clip: int = RUL_CLIP, with_rul: bool = True
) -> pd.DataFrame:
    """clean → (RUL label) → rolling features, ready for modelling."""
    out = clean(df)
    if with_rul:
        out = add_rul_label(out, clip=clip)
    return add_rolling_features(out, window=window)


def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split a labelled frame into features X and target y.

    Drops identifiers (``unit_id``, ``cycle``) so the model must read sensor
    health rather than memorising engine age.
    """
    if "rul" not in frame.columns:
        raise ValueError("Frame has no 'rul' column — call add_rul_label first")
    y = frame["rul"].astype("float64")
    X = frame.drop(columns=["unit_id", "cycle", "rul"])
    return X, y
