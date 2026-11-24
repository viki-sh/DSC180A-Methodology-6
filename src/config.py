"""Single source of truth for paths, columns, and split dates."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "bike_daily.csv"
PROCESSED = ROOT / "data" / "processed" / "features.parquet"
METRICS = ROOT / "reports" / "metrics.json"
EX4_TEST = ROOT / "reports" / "exercise4_test.json"  # written once, by --touch-test

# Daily Capital Bikeshare counts (Fanaee-T & Gama). Canonical home:
#   https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
# We use the processed copy from Molnar's "Interpretable Machine Learning"
# because the UCI host blocks some campus networks. It differs from UCI:
#   - 728 rows, 2011-01-03 to 2012-12-31 (UCI has 731 from 2011-01-01)
#   - 2011-03-10 is absent (the UCI row records humidity 0, a sensor
#     artefact, and the mirror's cleaning dropped the whole day)
#   - `weather` is the labels GOOD / MISTY / BAD, not UCI's codes 1-4
#   - two extra columns: `days_since_2011` and `cnt_2d_bfr`
DATA_URL = (
    "https://raw.githubusercontent.com/christophM/"
    "interpretable-ml-book/master/data/bike.csv"
)
# sha256 of the checked-in copy. src.ingest.load_raw refuses any other bytes,
# so every `make` stage and every test fails if data/raw/ is overwritten --
# including by a Bash `cp`, which the Write/Edit deny rules cannot see.
RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"

TARGET = "cnt"

# --- Three reasons a column is kept out of the feature set --------------

# 1. Leakage: the target or an arithmetic restatement of it.
#    casual + registered == cnt exactly, on every row. A model handed these
#    scores R^2 ~ 1.0 and has learned addition. At prediction time you would
#    not know either input: they are components of the thing being predicted.
LEAKAGE_COLS = {"casual", "registered", "cnt"}

# 2. Time indexes: not leakage, but a bad bet. A tree splits on "after date
#    X" and predicts a flat constant for every future date; a linear model
#    extrapolates a two-year trend we have no reason to trust. Excluding
#    them keeps the model comparison about what each does with lagged demand.
TIME_INDEX_COLS = {"instant", "yr", "days_since_2011"}

# 3. Unverified: `cnt_2d_bfr` is a two-day lag of cnt that shipped with the
#    mirror. It is NOT leakage -- a two-day-old count is known at prediction
#    time -- but we did not build it and cannot test how it was aligned, so we
#    build our own lags from the target and test those instead.
UNVERIFIED_COLS = {"cnt_2d_bfr"}

# What feature_columns() and the tests actually enforce.
FORBIDDEN = LEAKAGE_COLS | TIME_INDEX_COLS | UNVERIFIED_COLS

# --- Every other raw column, classified -----------------------------------
# feature_columns() keeps any numeric column not in FORBIDDEN, so a new
# numeric column in the CSV (say, a same-day count) would reach the model
# with nobody deciding it should. src.ingest.load_raw refuses any column
# that is not in exactly one of these sets or FORBIDDEN.

# 4. Same-day weather measurements, used as-is. `atemp` (feels-like) is on
#    an undocumented scale, r = 0.99 with `temp`; harmless, just not Celsius.
RAW_FEATURE_COLS = {"temp", "atemp", "hum", "windspeed"}
# 5. Text flags re-encoded in src/features.py; the encoded column is the feature.
ENCODED_COLS = {"holiday", "workday", "weather"}
# 6. Restatements of the date; calendar features are built from `dteday` itself.
CALENDAR_COLS = {"season", "mnth", "weekday"}
# 7. The date every row and every lag is aligned on.
KEY_COLS = {"dteday"}

CLASSIFIED = FORBIDDEN | RAW_FEATURE_COLS | ENCODED_COLS | CALENDAR_COLS | KEY_COLS

# Temporal split: train on 2011, validate on H1 2012, test on H2 2012.
TRAIN_END = "2011-12-31"
VALID_END = "2012-06-30"

# Longest lag window in src/features.py. The first LAG_WARMUP calendar days
# have no complete history and are dropped; tests/test_contract.py uses this
# to bound how many rows may legitimately disappear.
LAG_WARMUP = 7
