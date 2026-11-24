"""Stage 1: fetch the raw dataset and assert its shape.

Run: python -m src.ingest
"""
import hashlib
import sys
import urllib.request

import pandas as pd

from src.config import CLASSIFIED, DATA_URL, RAW, RAW_SHA256

EXPECTED_MIN_ROWS = 700
REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


def unclassified_columns(columns) -> set[str]:
    """Raw columns that no set in src/config.py accounts for."""
    return set(columns) - CLASSIFIED


def download(force: bool = False) -> None:
    if RAW.exists() and not force:
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, RAW)


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_raw() -> pd.DataFrame:
    digest = sha256(RAW)
    if digest != RAW_SHA256:
        raise ValueError(
            f"{RAW.name} has sha256 {digest[:16]}, not {RAW_SHA256[:16]}: data/raw/ is "
            "immutable. Restore it with `git checkout -- data/raw/`."
        )
    df = pd.read_csv(RAW, parse_dates=["dteday"])
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
    if len(df) < EXPECTED_MIN_ROWS:
        raise ValueError(f"raw data has only {len(df)} rows; expected >= {EXPECTED_MIN_ROWS}")
    new = unclassified_columns(df.columns)
    if new:
        raise ValueError(
            f"unclassified raw columns {sorted(new)}: put each in a set in "
            "src/config.py, with a reason, before it can reach the model"
        )
    return df


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    df = load_raw()
    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}, "
          f"sha256 {RAW_SHA256[:16]}")
