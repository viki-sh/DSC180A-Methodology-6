# Seeded faults (Exercise 2)

Each fault is its own commit (`fault N: ...`), followed by the commit that
fixes it, so `git show` on the fault commit is the exact change.

How the output below was produced:

- **Red test output:** fault 1 (by hand): `make test`, trimmed to the
  failing test's traceback and the summary. Faults 2-3: `record.sh` runs
  `python3 -m pytest tests -q --tb=short` and keeps the last 25 lines.
- **Hook stderr:** `.claude/hooks/check_leakage.sh` fed, on stdin, the
  PostToolUse payload Claude Code sends for the seeding Edit (`tool_name`
  `Edit`, `tool_input.file_path` the edited file). Fault 1 was done by
  hand; faults 2 and 3 used `.claude/skills/seed-fault/record.sh`, which does
  the same replay and writes the record.
- **Turns:** tool calls spent fixing, from the first edit after the red
  output through the first green `make test` (the fault commit in between is
  bookkeeping and not counted). The agent that fixed
  each fault (Claude Opus 5.5) also seeded it and knew the change, so these
  counts are lower bounds, not a measure of how hard the fault is to find.
- **Environment:** Linux, Python 3.13, the versions pinned in
  `requirements.txt` except pyarrow, which could not be installed there; its
  parquet read/write went through a pickle shim kept outside the repo. Values
  are unaffected: the starter's `make all` reproduced the tutorial's
  published metrics table to every digit.

## Fault 1: a forbidden column in `feature_columns`

Exact change (commit `fault 1: add a forbidden column (registered) to feature_columns`):

```diff
diff --git a/src/features.py b/src/features.py
index f3e3fa9..a0a5e60 100644
--- a/src/features.py
+++ b/src/features.py
@@ -86,7 +86,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
 def feature_columns(df: pd.DataFrame) -> list[str]:
     """Numeric columns that are safe to feed the model."""
     numeric = df.select_dtypes(include="number").columns
-    return [c for c in numeric if c not in FORBIDDEN]
+    return [c for c in numeric if c not in FORBIDDEN] + ["registered"]
 
 
 if __name__ == "__main__":
```

Red test output:

```
    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
E       assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', 'hum', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_contract.py::test_raw_columns_reach_the_model_only_if_classified_as_features
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
2 failed, 17 passed in 1.01s
make: *** [Makefile:16: test] Error 1
make test exit=2
```

Hook stderr (`hook exit=2`):

```
Leakage tests failed after editing /home/claude/bikeshare-open/src/features.py:
feats =         dteday  instant  season  ...  cnt_lag_1 cnt_lag_7   cnt_roll_7
0   2011-01-10     10.0  WINTER  ...      822.0...    1787.0  1530.142857
713 2012-12-31    731.0  WINTER  ...     1796.0     920.0  1531.428571

[714 rows x 29 columns]

    def test_no_forbidden_features(feats):
        """Guards the gate, not the data: feature_columns() excludes FORBIDDEN by
        construction, so this cannot discover a *new* leaky column. What it
        catches is someone editing feature_columns() or FORBIDDEN -- which is
        exactly the fault the Step 7 hook demonstrates."""
        cols = set(feature_columns(feats))
>       assert not (cols & FORBIDDEN), f"forbidden columns in feature set: {cols & FORBIDDEN}"
E       AssertionError: forbidden columns in feature set: {'registered'}
E       assert not ({'atemp', 'cnt_lag_1', 'cnt_lag_7', 'cnt_roll_7', 'dayofweek', 'hum', ...} & {'casual', 'cnt', 'cnt_2d_bfr', 'days_since_2011', 'instant', 'registered', ...})

tests/test_leakage.py:31: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 7 passed in 0.10s
```

Turns to fix: **2** (one Edit removing `+ ["registered"]`, one `make test`:
`19 passed in 1.05s`). Two tests caught it: the starter's `test_no_forbidden_features`
and the new `test_raw_columns_reach_the_model_only_if_classified_as_features`.

## Fault 2: delete the .shift(1) from cnt_roll_7

Exact change (`git diff HEAD`):

```diff
diff --git a/src/features.py b/src/features.py
index f3e3fa9..17c7803 100644
--- a/src/features.py
+++ b/src/features.py
@@ -78,7 +78,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
     out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
-    out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
+    out["cnt_roll_7"] = out[TARGET].rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
 
```

Test output (`python3 -m pytest tests -q --tb=short`, last 25 lines, exit 1):

```
............F......                                                      [100%]
=================================== FAILURES ===================================
_______________________ test_rolling_mean_excludes_today _______________________
tests/test_leakage.py:57: in test_rolling_mean_excludes_today
    assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E   assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E     
E     comparison failed
E     Obtained: 4389.0
E     Expected: 4414.857142857143 ± 0.00441486
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 18 passed in 1.18s
```

Hook stderr for an Edit of `src/features.py` (exit 2):

```
Leakage tests failed after editing /home/claude/bikeshare-open/src/features.py:
[714 rows x 29 columns]

    def test_rolling_mean_excludes_today(feats):
        """cnt_roll_7 must be the mean of the 7 calendar days *before* today."""
        by_date = feats.set_index("dteday")[TARGET]
        date = feats.dteday.iloc[200]
        window = [date - pd.Timedelta(days=k) for k in range(1, 8)]
        if all(d in by_date.index for d in window):
            expected = sum(by_date[d] for d in window) / 7
>           assert feats.set_index("dteday").cnt_roll_7[date] == pytest.approx(expected)
E           assert np.float64(4389.0) == 4414.857142857143 ± 0.00441486
E             
E             comparison failed
E             Obtained: 4389.0
E             Expected: 4414.857142857143 ± 0.00441486

tests/test_leakage.py:57: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_rolling_mean_excludes_today - assert np.fl...
1 failed, 7 passed in 0.15s
```


Turns to fix: 2 (one Edit restoring `.shift(1)` before `.rolling(LAG_WARMUP)`, one `make test`: `19 passed in 0.95s`). Only one test guards this shift, and it checks a single date (row 200).

## Fault 3: remove the raise from the weather encoder

Exact change (`git diff HEAD`):

```diff
diff --git a/src/features.py b/src/features.py
index f3e3fa9..86c4096 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
```

Test output (`python3 -m pytest tests -q --tb=short`, last 25 lines, exit 0):

```
...................                                                      [100%]
19 passed in 0.98s
```

Hook stderr for an Edit of `src/features.py` (exit 0):

```
<empty>
```


## Fault 3: remove the raise from the weather encoder, with the new test

Exact change (`git diff HEAD`):

```diff
diff --git a/src/features.py b/src/features.py
index f3e3fa9..86c4096 100644
--- a/src/features.py
+++ b/src/features.py
@@ -26,8 +26,6 @@ def encode_weather(series: pd.Series) -> pd.Series:
     """
     known = series.dropna()
     unknown = set(known.unique()) - set(WEATHER_ORDER)
-    if unknown:
-        raise ValueError(f"unmapped weather labels: {sorted(unknown)}")
     return series.map(WEATHER_ORDER).astype(float)
 
 
diff --git a/tests/test_leakage.py b/tests/test_leakage.py
index 5d56c64..a894d2e 100644
--- a/tests/test_leakage.py
+++ b/tests/test_leakage.py
@@ -72,6 +72,16 @@ def test_weather_lag_is_true_calendar_lag(feats):
     assert checked > 600, "too few rows actually verified"
 
 
+def test_unmapped_weather_label_fails_loudly():
+    """A silent .map() turns an unseen label into NaN and dropna() deletes
+    the row without a word -- how the 20 BAD days once vanished. Every real
+    label is mapped, so the data alone can never trip this; inject one."""
+    raw = load_raw()
+    raw.loc[raw.index[100], "weather"] = "SNOW"
+    with pytest.raises(ValueError, match="unmapped weather labels"):
+        build_features(raw)
+
+
 def test_no_missing_values(feats):
     assert feats[feature_columns(feats)].isna().sum().sum() == 0
 
```

Test output (`python3 -m pytest tests -q --tb=short`, last 25 lines, exit 1):

```
..............F.....                                                     [100%]
=================================== FAILURES ===================================
___________________ test_unmapped_weather_label_fails_loudly ___________________
tests/test_leakage.py:81: in test_unmapped_weather_label_fails_loudly
    with pytest.raises(ValueError, match="unmapped weather labels"):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE ValueError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_unmapped_weather_label_fails_loudly - Fail...
1 failed, 19 passed in 1.29s
```

Hook stderr for an Edit of `src/features.py` (exit 2):

```
Leakage tests failed after editing /home/claude/bikeshare-open/src/features.py:
......F..                                                                [100%]
=================================== FAILURES ===================================
___________________ test_unmapped_weather_label_fails_loudly ___________________

    def test_unmapped_weather_label_fails_loudly():
        """A silent .map() turns an unseen label into NaN and dropna() deletes
        the row without a word -- how the 20 BAD days once vanished. Every real
        label is mapped, so the data alone can never trip this; inject one."""
        raw = load_raw()
        raw.loc[raw.index[100], "weather"] = "SNOW"
>       with pytest.raises(ValueError, match="unmapped weather labels"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE ValueError

tests/test_leakage.py:81: Failed
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_unmapped_weather_label_fails_loudly - Fail...
1 failed, 8 passed in 0.09s
```


Turns to fix: 2 (one Edit restoring the two-line `raise`, keeping the new test; one `make test`: `20 passed in 1.20s`). The real finding is the GREEN run above: with the starter suite this fault was invisible to both the tests and the hook.
