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
- **Turns:** one turn is one tool call by the agent, counted from seeing the
  red output to the first green `make test`, inclusive. The agent that fixed
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
