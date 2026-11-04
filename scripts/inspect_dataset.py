r"""Phase 3 / Step 1 — inspect the extracted NASA C-MAPSS dataset.

Read-only. Prints an evidence report (no hard-coded facts): file inventory,
shapes, dtypes, missing values, duplicates, engine/cycle ranges and the
target-variable summary for every subset.

Run from the repo root:

    .venv\Scripts\python.exe scripts\inspect_dataset.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ingest import COLUMNS, RAW_DIR, SUBSETS  # noqa: E402

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 30)


def inventory(raw_dir: Path) -> None:
    print("=" * 78)
    print("FILE INVENTORY")
    print("=" * 78)
    files = sorted(p for p in raw_dir.rglob("*") if p.is_file())
    for p in files:
        rel = p.relative_to(raw_dir)
        print(f"  {str(rel):<60} {p.stat().st_size / 1024:>9,.1f} KB")
    print(f"\n  total files: {len(files)}")


def describe_table(path: Path, label: str) -> pd.DataFrame:
    """Read a raw table the same way production does, then profile it."""
    df = pd.read_csv(path, sep=r"\s+", header=None).dropna(axis=1, how="all")
    df.columns = COLUMNS[: df.shape[1]]
    print(f"\n--- {label} ({path.name}) ---")
    print(f"  shape          : {df.shape[0]:,} rows x {df.shape[1]} cols")
    dtypes = {str(k): int(v) for k, v in df.dtypes.astype(str).value_counts().items()}
    print(f"  dtypes         : {dtypes}")
    print(f"  missing values : {int(df.isna().sum().sum())}")
    print(f"  duplicate rows : {int(df.duplicated().sum())}")
    if {"unit_id", "cycle"} <= set(df.columns):
        print(f"  engines        : {df['unit_id'].nunique():,}")
        print(f"  cycles/engine  : min {int(df.groupby('unit_id')['cycle'].min().min())}"
              f", median {df.groupby('unit_id')['cycle'].max().median():.0f}"
              f", max {int(df.groupby('unit_id')['cycle'].max().max())}")
        dup_keys = int(df.duplicated(subset=["unit_id", "cycle"]).sum())
        print(f"  duplicate keys : {dup_keys}")
    return df


def main() -> None:
    raw = Path(RAW_DIR)
    if not raw.exists():
        raise SystemExit(f"Dataset folder not found: {raw}")

    inventory(raw)

    for subset in SUBSETS:
        print("\n" + "=" * 78)
        print(f"SUBSET {subset}")
        print("=" * 78)

        train = describe_table(raw / f"train_{subset}.txt", "train")
        describe_table(raw / f"test_{subset}.txt", "test")

        rul = pd.read_csv(raw / f"RUL_{subset}.txt", sep=r"\s+", header=None)
        rul = rul.dropna(axis=1, how="all").iloc[:, 0]
        print(f"\n--- RUL_{subset}.txt ---")
        print(f"  values         : {len(rul):,} (one per test engine)")
        print(f"  min / median / max : {rul.min()} / {rul.median():.0f} / {rul.max()}")

        # Constant columns carry no signal — the feature set will drop them.
        nunique = train.drop(columns=["unit_id", "cycle"]).nunique()
        constant = [c for c in nunique.index if nunique[c] == 1]
        print(f"\n  constant columns ({len(constant)}): {constant if constant else 'none'}")
        print(f"  usable raw features: {train.shape[1] - 2 - len(constant)}")

    print("\n" + "=" * 78)
    print("TARGET")
    print("=" * 78)
    print("  train_*.txt : run-to-failure, so RUL is derived per row as")
    print("                last_cycle(engine) - cycle, clipped at 125 cycles.")
    print("  test_*.txt  : truncated trajectories; true RUL at each engine's")
    print("                last cycle is given in RUL_*.txt.")
    print("  There is no 'RUL' column inside train/test files - it is derived.")


if __name__ == "__main__":
    main()
