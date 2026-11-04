"""Backend configuration — environment wins, safe defaults for local dev."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("SHM_DB_PATH", ROOT / "data" / "shm.db"))
MODELS_DIR = Path(os.environ.get("SHM_MODELS_DIR", ROOT / "models"))
SUBSET = os.environ.get("SHM_SUBSET", "FD001")

#: When set, mutating endpoints require ``X-API-Token``. Empty = open demo mode.
API_TOKEN = os.environ.get("SHM_API_TOKEN", "")

#: Comma-separated origins, or ``*`` for any. Read-only API, so ``*`` is safe;
#: writes are guarded by the token above.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("SHM_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

DATASET = {
    "name": "NASA C-MAPSS Turbofan Engine Degradation Simulation Data Set",
    "source": "NASA Prognostics Center of Excellence",
    "license": "Public domain (U.S. Government work)",
    "subset": SUBSET,
    "sensors": 21,
    "settings": 3,
}
