# Data — NASA C-MAPSS Turbofan Engine Degradation

## What it is

Official NASA benchmark: run-to-failure sensor readings from simulated turbofan engines.
**21 sensors + 3 operating settings** per cycle, with **true Remaining Useful Life (RUL)**
labels for evaluation. Four subsets of increasing difficulty:

| Subset | Engines (train) | Difficulty |
|---|---|---|
| FD001 | 100 | simplest — our starting point |
| FD002 | 260 | + 6 operating conditions |
| FD003 | 100 | + 2 fault modes |
| FD004 | 249 | hardest (all of the above) |

## Where it comes from

- Case-study link: `data.nasa.gov/dataset/cmapss-jet-engine-simulated-data`
- Direct download (found from the NASA Prognostics CoE repository page):
  `https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip`

## How it is laid out in this folder (not committed — see .gitignore)

```
data/
├── raw/
│   ├── CMAPSS_Turbofan.zip                    ← downloaded archive
│   └── cmapss/data/
│       ├── train_FD001.txt … train_FD004.txt  ← run-to-failure training data
│       ├── test_FD001.txt  … test_FD004.txt   ← truncated test trajectories
│       ├── RUL_FD001.txt  … RUL_FD004.txt     ← true RUL per test engine
│       ├── readme.txt
│       └── Damage Propagation Modeling.pdf
└── processed/                                  ← built by pipeline/dataset.py (gitignored)
    ├── fd001_train.parquet                    features + derived rul label
    ├── fd001_test.parquet                     features only (no label — leakage guard)
    ├── fd001_test_rul.parquet                 official truth, one row per test engine
    └── fd001_manifest.json                    window, clip, counts, sha256 per file
```

## Rebuild the processed dataset in one command

```powershell
.venv\Scripts\python.exe -m pipeline.dataset --subsets all
```

Expected output (verified 2026-11-04):

```
FD001: train 20,631x90 (100 engines) | test 13,096x89 (100 engines) | 87 features
FD002: train 53,759x90 (260 engines) | test 33,991x89 (259 engines) | 87 features
FD003: train 24,720x90 (100 engines) | test 16,596x89 (100 engines) | 87 features
FD004: train 61,249x90 (249 engines) | test 41,214x89 (248 engines) | 87 features
```

Every frame is validated before it is written: unique `(unit_id, cycle)` keys,
no NaN/inf, numeric-only columns, `cycle >= 1`, non-negative RUL. Identical
runs produce identical sha256 hashes (proven by `tests/test_dataset.py`).

## Column format (space separated, no header)

```
unit_id  cycle  setting_1  setting_2  setting_3  sensor_1 … sensor_21
```

26 columns. `RUL_FD00x.txt` has one integer per test engine.

## Re-download in one command

```powershell
curl.exe -L -o data\raw\CMAPSS_Turbofan.zip "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
Expand-Archive data\raw\CMAPSS_Turbofan.zip data\raw\cmapss -Force
Expand-Archive "data\raw\cmapss\6. Turbofan Engine Degradation Simulation Data Set\CMAPSSData.zip" data\raw\cmapss\data -Force
```
