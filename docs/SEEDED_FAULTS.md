# Seeded faults (Exercise 2)

Each fault is its own commit (subject starting `fault`), followed by the
commit that fixes it, so `git show` on the fault commit is the exact change.
Fault 4 is the exception: its tampered CSV was never committed, so the
fault and its fix share one commit, with the fix described in the message.

| # | Fault | What went red | Hook | Turns to fix |
|---|---|---|---|---|
| 1 | `registered` added to `feature_columns` | `test_no_forbidden_features`, `test_raw_columns_reach_the_model_only_if_classified_as_features` | exit 2 | 2 |
| 2 | `.shift(1)` deleted from `cnt_roll_7` | `test_rolling_mean_excludes_today` | exit 2 | 2 |
| 3 | `raise` removed from `encode_weather` | nothing; then the new `test_unmapped_weather_label_fails_loudly` | exit 0, then 2 | 2 |
| 4 | Bash `cp` over `data/raw/bike_daily.csv` | nothing (20 passed); now the sha256 check fails every stage and test | never runs for Bash | none, then 2 |
| 5 | `.shift(LAG_WARMUP)` deleted from `cnt_lag_7` | nothing (ridge R^2 0.9999); then the new `test_every_target_lag_matches_the_calendar` | exit 0, then 2 | 2 |

How the output below was produced:

- **Red test output:** fault 1 (by hand): `make test`, trimmed to the
  failing test's traceback and the summary. Faults 2, 3, 5: `record.sh` runs
  `python3 -m pytest tests -q --tb=short` and keeps the last 25 lines.
- **Hook stderr:** `.claude/hooks/check_leakage.sh` fed, on stdin, the
  PostToolUse payload Claude Code sends for the seeding Edit (`tool_name`
  `Edit`, `tool_input.file_path` the edited file). Faults 1 and 4 were
  done by hand; faults 2, 3 and 5 used `.claude/skills/seed-fault/record.sh`,
  which does the same replay and writes the record. Fault 5 is beyond the
  four the assignment asks for: it came from dry-running the skill.
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

## Before the feature: the new test, red (Exercise 1)

`test_weather_lag_is_true_calendar_lag` was written before
`weather_severity_lag_1` existed. It failed for the right reason: the
column is missing. The failing run below was re-run on 2026-11-25 by
checking out commit `test: failing test for weather_severity_lag_1` and
running `make test`. It is trimmed to the header, the error and the summary:

```
python -m pytest tests/ -q
.........F.....                                                          [100%]
=================================== FAILURES ===================================
____________________ test_weather_lag_is_true_calendar_lag _____________________
    ...  (traceback trimmed)
E       AttributeError: 'DataFrame' object has no attribute 'weather_severity_lag_1'. Did you mean: 'weather_severity'?

/usr/local/lib/python3.13/site-packages/pandas/core/generic.py:6194: AttributeError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_lag_is_true_calendar_lag - Attribu...
1 failed, 14 passed in 1.29s
make: *** [Makefile:16: test] Error 1
```

The original run on 2026-11-23, before the feature commit, ended the same
way:

```
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_weather_lag_is_true_calendar_lag - Attribu...
1 failed, 14 passed in 1.19s
make: *** [Makefile:16: test] Error 1
```

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

Turns to fix: 2 (one Edit removing `+ ["registered"]`, one `make test`:
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

## Fault 4: overwrite `data/raw/` with a Bash `cp`, which the hook cannot see

Done by hand, in the working tree only. The tampered CSV was never
committed. The "cleanup" is one an over-eager agent might do: drop the
Hurricane Sandy day (22 rides) from the raw file. State before any new
guard (at commit `exercise 4: touch the test set once, for the pre-registered pairs`):

```
$ git status --short; sha256sum data/raw/bike_daily.csv
a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc  data/raw/bike_daily.csv

$ grep -v '"2012-10-29"' data/raw/bike_daily.csv > /tmp/bike_clean.csv && cp /tmp/bike_clean.csv data/raw/bike_daily.csv
(exit 0, no output)

$ # PostToolUse hook, fed the payload of that Bash call (its matcher is Edit|Write, so Claude Code never calls it for Bash at all):
hook exit=0 (stderr empty)

$ make test
....................                                                     [100%]
20 passed in 1.00s

$ make all   # ingest + features lines, then the changed test scores
OK ingest: 727 rows, 2011-01-03 -> 2012-12-31
OK features: 706 rows, 15 features -> features.parquet

$ git diff --stat; git diff -U0 reports/metrics.json
 data/raw/bike_daily.csv |  1 -
 reports/metrics.json    | 18 +++++++++---------
 2 files changed, 9 insertions(+), 10 deletions(-)
-  "n_test": 184,
+  "n_test": 176,
-      "r2": -2.1441,
-      "mae": 2847.7
+      "r2": -2.4693,
+      "mae": 2876.0
-      "r2": 0.5099,
-      "mae": 840.1
+      "r2": 0.53,
+      "mae": 813.3
-      "r2": 0.6124,
-      "mae": 910.6
+      "r2": 0.6243,
+      "mae": 875.7
-      "r2": -0.4687,
-      "mae": 1950.4
+      "r2": -0.6165,
+      "mae": 1967.0

$ sha256sum data/raw/bike_daily.csv
a93dc1924f67db7e52ed954327dd910a29bfe8a248dc36bc34f0b734b68c96e1  data/raw/bike_daily.csv
```

**What happened:** nothing went red.

- **Hook:** the PostToolUse matcher is `Edit|Write`, so Claude Code never
  runs the hook for a Bash call. It would have ignored the payload anyway,
  because there is no `file_path`.
- **Permissions:** the deny rules `Write(./data/raw/**)` and
  `Edit(./data/raw/**)` bind those two tools, not a shell `cp`. Because `cp`
  is not in the allow list, the only defence in default mode was a human
  reading the approval prompt.
- **Pipeline:** all 20 tests passed and `make all` ran. The test set silently
  lost 8 days (Sandy, plus the 7 rows whose lags span the new gap). Every
  test score moved, and ridge and persistence both looked better: ridge
  0.6124 -> 0.6243, persistence 0.5099 -> 0.5300.
- **Detection:** only `git status` and the sha256 showed it.

**What would have caught it, and what now does** (commit `fault 4: ...`):

1. **A hash check in `make data`.** `src/ingest.load_raw` compares the file to
   `RAW_SHA256` in `src/config.py`. Every make stage and every test loads
   the raw file through it, so any write path fails loudly: Bash, an
   editor, or a re-download from a changed mirror. This is the guarantee.
2. **A `PreToolUse` hook on Bash** (`.claude/hooks/guard_raw.sh`). It blocks
   the obvious commands before they run. It is a speed bump, not a
   guarantee: a glob dodges its string match, as shown below.
3. **A `Stop` hook** (`.claude/hooks/stop_gate.sh`). The agent cannot declare
   itself done while `make test` is red.
4. **Not used: a filesystem permission** (`chmod a-w`). git does not track
   the write bit, so it would not survive a fresh clone.

Diff of the guard in `src/` and `.claude/settings.json` (commit `fault 4:
...`, `git show -- src/config.py src/ingest.py .claude/settings.json`). The
two new hook scripts are `.claude/hooks/guard_raw.sh` and
`.claude/hooks/stop_gate.sh`.

```diff
diff --git a/.claude/settings.json b/.claude/settings.json
index 5c849d8..6cb5400 100644
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -7,6 +7,19 @@
     "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"
   },
   "hooks": {
+    "PreToolUse": [
+      {
+        "matcher": "Bash",
+        "hooks": [
+          {
+            "type": "command",
+            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/guard_raw.sh",
+            "timeout": 10,
+            "statusMessage": "Checking the command does not write into data/raw/..."
+          }
+        ]
+      }
+    ],
     "PostToolUse": [
       {
         "matcher": "Edit|Write",
@@ -19,6 +32,18 @@
           }
         ]
       }
+    ],
+    "Stop": [
+      {
+        "hooks": [
+          {
+            "type": "command",
+            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/stop_gate.sh",
+            "timeout": 120,
+            "statusMessage": "Running the test suite before finishing..."
+          }
+        ]
+      }
     ]
   },
   "permissions": {
diff --git a/src/config.py b/src/config.py
index 44963e3..fc00450 100644
--- a/src/config.py
+++ b/src/config.py
@@ -20,6 +20,10 @@ DATA_URL = (
     "https://raw.githubusercontent.com/christophM/"
     "interpretable-ml-book/master/data/bike.csv"
 )
+# sha256 of the checked-in copy. src.ingest.load_raw refuses any other bytes,
+# so every `make` stage and every test fails if data/raw/ is overwritten --
+# including by a Bash `cp`, which the Write/Edit deny rules cannot see.
+RAW_SHA256 = "a6bed1577f6e4de56dcfae6d8315985073cc0ad3446c8c99ed60c86a0b5ad9dc"
 
 TARGET = "cnt"
 
diff --git a/src/ingest.py b/src/ingest.py
index a626733..b0436b1 100644
--- a/src/ingest.py
+++ b/src/ingest.py
@@ -2,12 +2,13 @@
 
 Run: python -m src.ingest
 """
+import hashlib
 import sys
 import urllib.request
 
 import pandas as pd
 
-from src.config import CLASSIFIED, DATA_URL, RAW
+from src.config import CLASSIFIED, DATA_URL, RAW, RAW_SHA256
 
 EXPECTED_MIN_ROWS = 700
 REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}
@@ -25,7 +26,17 @@ def download(force: bool = False) -> None:
     urllib.request.urlretrieve(DATA_URL, RAW)
 
 
+def sha256(path) -> str:
+    return hashlib.sha256(path.read_bytes()).hexdigest()
+
+
 def load_raw() -> pd.DataFrame:
+    digest = sha256(RAW)
+    if digest != RAW_SHA256:
+        raise ValueError(
+            f"{RAW.name} has sha256 {digest[:16]}, not {RAW_SHA256[:16]}: data/raw/ is "
+            "immutable. Restore it with `git checkout -- data/raw/`."
+        )
     df = pd.read_csv(RAW, parse_dates=["dteday"])
     missing = REQUIRED_COLS - set(df.columns)
     if missing:
@@ -44,4 +55,5 @@ def load_raw() -> pd.DataFrame:
 if __name__ == "__main__":
     download(force="--force" in sys.argv)
     df = load_raw()
-    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}")
+    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}, "
+          f"sha256 {RAW_SHA256[:16]}")
```

The same attack against the new guards:

```
$ # PreToolUse hook, fed the payload of the same Bash call:
Blocked by guard_raw.sh: this command would write into data/raw/, which is immutable (make data checks its sha256). Read it with pandas, head, wc or sha256sum; write derived files to data/processed/. To undo a change: git checkout -- data/raw/
guard exit=2

$ # A glob dodges the string match (guard exit 0), so the overwrite lands:
guard exit=0
$ cp /tmp/bike_clean.csv data/r?w/bike_daily.cs?
(exit 0)

$ make data
    )
ValueError: bike_daily.csv has sha256 a93dc1924f67db7e, not a6bed1577f6e4de5: data/raw/ is immutable. Restore it with `git checkout -- data/raw/`.
make: *** [Makefile:7: data] Error 1

$ make test
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: bike...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: bike_daily...
1 failed, 3 passed, 17 errors in 1.18s
make: *** [Makefile:16: test] Error 1

$ # Stop hook, fed a Stop payload (stop_hook_active false):
Not done: the test suite is red. Fix it, or say plainly why you cannot.
ERROR tests/test_contract.py::test_calendar_is_complete_before_lagging - Valu...
ERROR tests/test_contract.py::test_only_expected_rows_are_dropped - ValueErro...
ERROR tests/test_contract.py::test_beats_the_mean_baseline - ValueError: bike...
ERROR tests/test_leakage.py::test_leakage_identity_holds - ValueError: bike_d...
ERROR tests/test_leakage.py::test_no_forbidden_features - ValueError: bike_da...
ERROR tests/test_leakage.py::test_lags_are_true_calendar_lags - ValueError: b...
ERROR tests/test_leakage.py::test_lag_is_not_the_target - ValueError: bike_da...
ERROR tests/test_leakage.py::test_rolling_mean_excludes_today - ValueError: b...
ERROR tests/test_leakage.py::test_weather_lag_is_true_calendar_lag - ValueErr...
ERROR tests/test_leakage.py::test_no_missing_values - ValueError: bike_daily....
ERROR tests/test_leakage.py::test_dates_are_sorted_and_unique - ValueError: b...
ERROR tests/test_split.py::test_splits_non_empty - ValueError: bike_daily.csv...
ERROR tests/test_split.py::test_splits_are_ordered_in_time - ValueError: bike...
ERROR tests/test_split.py::test_no_overlapping_dates - ValueError: bike_daily...
1 failed, 3 passed, 17 errors in 1.06s
stop hook exit=2
```

```
$ git checkout -- data/raw/ && make data && make test
OK ingest: 728 rows, 2011-01-03 -> 2012-12-31, sha256 a6bed1577f6e4de5
21 passed in 1.09s
```

**Turns to fix:**

- **Before the guards:** none. Nothing went red, so nothing prompted a fix;
  the overwrite showed up only in `git status`.
- **After the guards:** 2 (`git checkout -- data/raw/`, then
  `make data && make test`: `21 passed`).

### Related: the PostToolUse hook was blind on Windows

While closing this gap I found two ways the starter hook passes silently on
a Windows machine:

- **Backslash paths:** Claude Code sends the edited path with backslashes,
  and `*src/*.py` never matches them.
- **The `python3` stub:** on many machines `python3` is a Store stub that
  exits non-zero. That left `$path` empty, and the hook exited 0.

The hook now normalises slashes and uses the first Python that actually
runs. Real output, with fault 1 re-seeded in the working tree:

```
$ # fault 1 re-seeded in the working tree; Edit payload with a Windows path (C:\Users\viki\bikeshare-open\src\features.py)
$ starter check_leakage.sh:
exit=0 stderr_lines=0
$ new check_leakage.sh:
exit=2 stderr: Leakage tests failed after editing C:/Users/viki/bikeshare-open/src/features.py:
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 8 passed in 0.12s

$ # same fault, POSIX path, but `python3` on PATH is a Store-style stub that exits non-zero (as on many Windows machines)
$ PATH=/tmp/stubbin:$PATH starter check_leakage.sh:
exit=0 stderr_lines=0
$ PATH=/tmp/stubbin:$PATH new check_leakage.sh:
exit=2 stderr: Leakage tests failed after editing /home/claude/bikeshare-open/src/features.py:
FAILED tests/test_leakage.py::test_no_forbidden_features - AssertionError: fo...
1 failed, 8 passed in 0.11s
```

## Fault 5: delete the .shift(LAG_WARMUP) from cnt_lag_7

Exact change (`git diff HEAD`):

```diff
diff --git a/src/features.py b/src/features.py
index f3e3fa9..0c542ab 100644
--- a/src/features.py
+++ b/src/features.py
@@ -77,7 +77,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # without it, cnt_roll_7 would contain today's count. -----------------
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
-    out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
+    out["cnt_lag_7"] = out[TARGET]
     out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
```

Test output (`python3 -m pytest tests -q --tb=short`, last 25 lines, exit 0):

```
..................s...                                                   [100%]
21 passed, 1 skipped in 0.98s
```

Hook stderr for an Edit of `src/features.py` (exit 0):

```
<empty>
```


## Fault 5: delete the .shift(LAG_WARMUP) from cnt_lag_7, with the new test

Exact change (`git diff HEAD`):

```diff
diff --git a/src/features.py b/src/features.py
index f3e3fa9..0c542ab 100644
--- a/src/features.py
+++ b/src/features.py
@@ -77,7 +77,7 @@ def build_features(df: pd.DataFrame) -> pd.DataFrame:
     # without it, cnt_roll_7 would contain today's count. -----------------
     # If you add a longer lag, raise LAG_WARMUP in src/config.py.
     out["cnt_lag_1"] = out[TARGET].shift(1)
-    out["cnt_lag_7"] = out[TARGET].shift(LAG_WARMUP)
+    out["cnt_lag_7"] = out[TARGET]
     out["cnt_roll_7"] = out[TARGET].shift(1).rolling(LAG_WARMUP).mean()
 
     return out.dropna().reset_index(drop=True)
diff --git a/tests/test_leakage.py b/tests/test_leakage.py
index a894d2e..7673607 100644
--- a/tests/test_leakage.py
+++ b/tests/test_leakage.py
@@ -72,6 +72,19 @@ def test_weather_lag_is_true_calendar_lag(feats):
     assert checked > 600, "too few rows actually verified"
 
 
+def test_every_target_lag_matches_the_calendar(feats):
+    """Recompute every lagged-target feature from raw counts by calendar date,
+    on every row. Nothing checked cnt_lag_7 before: setting it to today's
+    count (validation R^2 0.9999) left the whole suite green."""
+    cnt = load_raw().set_index("dteday")[TARGET]
+    day = pd.Timedelta(days=1)
+    for date, row in feats.set_index("dteday").iterrows():
+        assert row.cnt_lag_1 == cnt[date - day], f"cnt_lag_1 at {date.date()}"
+        assert row.cnt_lag_7 == cnt[date - 7 * day], f"cnt_lag_7 at {date.date()}"
+        window = [cnt[date - k * day] for k in range(1, 8)]
+        assert row.cnt_roll_7 == pytest.approx(sum(window) / 7), f"cnt_roll_7 at {date.date()}"
+
+
 def test_unmapped_weather_label_fails_loudly():
     """A silent .map() turns an unseen label into NaN and dropna() deletes
     the row without a word -- how the 20 BAD days once vanished. Every real
```

Test output (`python3 -m pytest tests -q --tb=short`, last 25 lines, exit 1):

```
...............F...s...                                                  [100%]
=================================== FAILURES ===================================
__________________ test_every_target_lag_matches_the_calendar __________________
tests/test_leakage.py:83: in test_every_target_lag_matches_the_calendar
    assert row.cnt_lag_7 == cnt[date - 7 * day], f"cnt_lag_7 at {date.date()}"
E   AssertionError: cnt_lag_7 at 2011-01-10
E   assert 1321.0 == np.int64(1349)
E    +  where 1321.0 = instant                        10.0\nseason                       WINTER\nyr                           2011.0\nmnth      ... 822.0\ncnt_lag_7                    1321.0\ncnt_roll_7                   1344.0\nName: 2011-01-10 00:00:00, dtype: object.cnt_lag_7
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_every_target_lag_matches_the_calendar - As...
1 failed, 21 passed, 1 skipped in 1.08s
```

Hook stderr for an Edit of `src/features.py` (exit 2):

```
Leakage tests failed after editing /home/claude/bikeshare-open/src/features.py:

[714 rows x 29 columns]

    def test_every_target_lag_matches_the_calendar(feats):
        """Recompute every lagged-target feature from raw counts by calendar date,
        on every row. Nothing checked cnt_lag_7 before: setting it to today's
        count (validation R^2 0.9999) left the whole suite green."""
        cnt = load_raw().set_index("dteday")[TARGET]
        day = pd.Timedelta(days=1)
        for date, row in feats.set_index("dteday").iterrows():
            assert row.cnt_lag_1 == cnt[date - day], f"cnt_lag_1 at {date.date()}"
>           assert row.cnt_lag_7 == cnt[date - 7 * day], f"cnt_lag_7 at {date.date()}"
E           AssertionError: cnt_lag_7 at 2011-01-10
E           assert 1321.0 == np.int64(1349)
E            +  where 1321.0 = instant                        10.0\nseason                       WINTER\nyr                           2011.0\nmnth      ... 822.0\ncnt_lag_7                    1321.0\ncnt_roll_7                   1344.0\nName: 2011-01-10 00:00:00, dtype: object.cnt_lag_7

tests/test_leakage.py:83: AssertionError
=========================== short test summary info ============================
FAILED tests/test_leakage.py::test_every_target_lag_matches_the_calendar - As...
1 failed, 9 passed in 0.12s
```


Turns to fix: 2 (one Edit restoring `.shift(LAG_WARMUP)`, keeping the new test; one `make test`: `22 passed, 1 skipped`). This one matters most: with the starter suite plus my earlier tests, a same-day leak through `cnt_lag_7` (ridge validation R^2 0.9999) was green everywhere.
