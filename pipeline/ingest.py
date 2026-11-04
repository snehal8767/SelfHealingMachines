"""Layer 1 — Data Engineering: load NASA C-MAPSS files into validated DataFrames.

Raw files are space separated with no header and end in trailing whitespace,
which pandas reads back as an extra all-NaN column. We drop that column and
apply the canonical names from the NASA readme:

    unit_id cycle setting_1 setting_2 setting_3 sensor_1 … sensor_21   (26 cols)

`RUL_FD00x.txt` holds one integer per *test* engine, in engine order.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SETTINGS = ["setting_1", "setting_2", "setting_3"]
SENSORS = [f"sensor_{i}" for i in range(1, 22)]  # 21 sensors
COLUMNS = ["unit_id", "cycle", *SETTINGS, *SENSORS]
SUBSETS = ("FD001", "FD002", "FD003", "FD004")

#: Where the extracted NASA files live (see data/README.md for re-download steps).
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw" / "cmapss" / "data"


def _read_table(path: Path) -> pd.DataFrame:
    """Read one space-separated C-MAPSS table with strict column validation."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing dataset file: {path}\n"
            "Download instructions: data/README.md"
        )
    df = pd.read_csv(path, sep=r"\s+", header=None)
    df = df.dropna(axis=1, how="all")  # trailing-whitespace artefact
    if df.shape[1] != len(COLUMNS):
        raise ValueError(
            f"{path.name}: expected {len(COLUMNS)} columns, got {df.shape[1]}"
        )
    df.columns = COLUMNS
    return df.astype({"unit_id": "int64", "cycle": "int64"})


def load_subset(subset: str = "FD001", raw_dir: Path | str = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Load one C-MAPSS subset.

    Returns
    -------
    dict with keys
      ``train`` — run-to-failure trajectories (labels derivable from cycle)
      ``test``  — truncated trajectories (unknown end of life)
      ``rul``   — true Remaining Useful Life per test engine, indexed 0..N-1
    """
    subset = subset.upper()
    if subset not in SUBSETS:
        raise ValueError(f"Unknown subset {subset!r}; expected one of {SUBSETS}")

    raw = Path(raw_dir)
    rul_path = raw / f"RUL_{subset}.txt"
    if not rul_path.exists():
        raise FileNotFoundError(
            f"Missing dataset file: {rul_path}\n"
            "Download instructions: data/README.md"
        )
    rul = pd.read_csv(rul_path, sep=r"\s+", header=None).dropna(axis=1, how="all")
    return {
        "train": _read_table(raw / f"train_{subset}.txt"),
        "test": _read_table(raw / f"test_{subset}.txt"),
        "rul": rul.iloc[:, 0].astype("int64").rename("rul").reset_index(drop=True),
    }
