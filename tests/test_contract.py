"""Guard rails on the ingest contract and the trained model's behaviour."""
import pandas as pd
import pytest
from sklearn.metrics import r2_score

from src.config import (
    CALENDAR_COLS,
    ENCODED_COLS,
    KEY_COLS,
    LAG_WARMUP,
    LEAKAGE_COLS,
    RAW_FEATURE_COLS,
    TARGET,
    TIME_INDEX_COLS,
    UNVERIFIED_COLS,
)
from src.features import build_features, feature_columns, reindex_to_calendar
from src.ingest import load_raw, unclassified_columns
from src.train import MODELS, temporal_split


@pytest.fixture(scope="module")
def raw():
    return load_raw().sort_values("dteday").reset_index(drop=True)


@pytest.fixture(scope="module")
def feats(raw):
    return build_features(raw)


def test_every_raw_column_is_classified(raw):
    """feature_columns() keeps every numeric column not in FORBIDDEN, so a
    column nobody has classified would reach the model unreviewed.
    test_no_forbidden_features cannot see that case; this test can."""
    assert not unclassified_columns(raw.columns)


def test_a_new_raw_column_is_flagged(raw):
    """The check must be able to fail: a same-day restatement of the target
    appended to the CSV is flagged instead of silently becoming a feature."""
    assert unclassified_columns([*raw.columns, "cnt_today"]) == {"cnt_today"}


def test_raw_columns_reach_the_model_only_if_classified_as_features(raw, feats):
    passthrough = set(feature_columns(feats)) & set(raw.columns)
    assert passthrough == RAW_FEATURE_COLS, f"raw columns used as features: {sorted(passthrough)}"


def test_each_column_has_exactly_one_reason():
    classes = [LEAKAGE_COLS, TIME_INDEX_COLS, UNVERIFIED_COLS,
               RAW_FEATURE_COLS, ENCODED_COLS, CALENDAR_COLS, KEY_COLS]
    assert sum(map(len, classes)) == len(set().union(*classes)), "a column is in two sets"


def test_tampered_raw_file_is_refused(tmp_path, monkeypatch):
    """The sha256 guard must be able to fail: drop one row (the Sandy day an
    over-eager cleanup would delete) and load_raw refuses the file."""
    import src.ingest as ingest

    lines = ingest.RAW.read_text().splitlines(keepends=True)
    tampered = tmp_path / "bike_daily.csv"
    tampered.write_text("".join(line for line in lines if '"2012-10-29"' not in line))
    monkeypatch.setattr(ingest, "RAW", tampered)
    with pytest.raises(ValueError, match="immutable"):
        ingest.load_raw()


def test_calendar_is_complete_before_lagging(raw):
    """The reindexed frame must have no gaps, or the lags are wrong."""
    grid = reindex_to_calendar(raw)
    assert set(grid.dteday.diff().dropna().dt.days.unique()) == {1}


def test_only_expected_rows_are_dropped(raw, feats):
    """Rows may only vanish for the lag warm-up or downstream of a genuinely
    absent day -- never because an encoder produced a silent NaN.

    Accounting: the first LAG_WARMUP days have no complete history. Each
    absent calendar day m costs the LAG_WARMUP rows after it (cnt_lag_1 is
    NaN on m+1, cnt_roll_7 is NaN on m+1..m+7, cnt_lag_7 on m+7; their
    union is 7 rows). Day m itself was never in `raw`, so it is not a loss.
    The bound is exact for the current feature set; add a longer lag and
    LAG_WARMUP in src/config.py must grow with it.
    """
    full = pd.date_range(raw.dteday.min(), raw.dteday.max(), freq="D")
    missing_days = len(full) - len(raw)
    allowed_loss = LAG_WARMUP + LAG_WARMUP * missing_days
    lost = len(raw) - len(feats)
    assert lost <= allowed_loss, f"lost {lost} rows; expected at most {allowed_loss}"


def test_beats_the_mean_baseline(feats):
    """A model that cannot beat predicting the training mean is not a result."""
    cols = feature_columns(feats)
    train, _, test = temporal_split(feats)
    ridge = MODELS["ridge"]
    ridge.fit(train[cols], train[TARGET])
    assert r2_score(test[TARGET], ridge.predict(test[cols])) > 0.4


def test_persistence_baseline_is_reported():
    """The baseline that matters for a lag-driven model is 'yesterday again'.
    It must be in the comparison, whatever its score."""
    assert "baseline_persistence" in MODELS
