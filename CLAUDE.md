# Bikeshare demand capstone

Daily Capital Bikeshare counts, 2011-2012. We forecast `cnt` (total daily
rides) one day ahead from calendar, weather, and lagged-demand features.

## Commands
- `make all` - data -> features -> train; writes `reports/metrics.json`
- `make test` - run this before claiming anything works
- `/new-feature <feature>` - add a feature, failing test first
- `/seed-fault <fault>` - break the pipeline on purpose, record the real
  output in `docs/SEEDED_FAULTS.md`, then fix it

## Non-negotiable rules
- **Never** put `casual` or `registered` in a feature set:
  `casual + registered == cnt` exactly. `FORBIDDEN` in `src/config.py`
  also bars the time indexes `instant`, `yr`, `days_since_2011` and the
  unverified `cnt_2d_bfr`. Derive feature lists from it; never hand-type them.
- **Never** split this data randomly. Use `src.train.temporal_split`:
  train 2011, valid H1 2012, test H2 2012. Never tune on test, and do not
  quote test numbers while iterating.
- Any new lag or rolling feature goes after `reindex_to_calendar` and
  must `.shift(1)` before it aggregates. Add a test for it in
  `tests/test_leakage.py`.
- Report the mean baseline **and** the persistence baseline (yesterday's
  count) beside every model. A negative R^2 is a finding, not a bug to hide.
- `data/raw/` is immutable by every route, including `cp`, `mv`, redirects
  and `sed -i` from Bash. `make data` checks its sha256; undo a change with
  `git checkout -- data/raw/`.
- A new raw column must be classified in `src/config.py`, with a reason,
  before it is used. `load_raw` refuses unclassified columns.
- When a hook or test blocks you, fix the cause. Never weaken a test, a
  hook, `FORBIDDEN`, or `.claude/settings.json` to get green.
- Experiments (`python -m src.train --target-transform ...`) never write
  `reports/metrics.json`. `--touch-test` is one-shot: never delete
  `reports/exercise4_test.json` to run it again.
- If the metrics change, rerun `make all` and update the `REPORT.md` table
  in the same commit. They must match to the printed digit.

## Style
- Standard library, pandas, scikit-learn only. No new dependencies
  without asking. Versions are pinned in `requirements.txt`.
- Paths and constants live in `src/config.py`. Nothing is hardcoded twice.
- One dated line in `docs/DECISIONS.md` per methodological decision.

## Gotchas
- The data is a mirror, not the UCI file: 728 rows from 2011-01-03, not
  731 from 2011-01-01, and 2011-03-10 is missing.
- Ridership grew ~65% from 2011 to 2012, so tree models trained on 2011
  cannot extrapolate to 2012. That is the headline result, not an error.
- 2012-10-29 (Hurricane Sandy, 22 rides) is in the test set. It is real
  data: never drop it, and expect it in any residual plot.
