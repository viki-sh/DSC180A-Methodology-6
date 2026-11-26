# Forecasting daily Capital Bikeshare demand

Daily `cnt` for Washington, DC, one day ahead. The models train on 2011
(348 days), are tuned on H1 2012 (validation, 182 days), and are tested on
H2 2012 (184 days).

## Results

"Before" is the starter pipeline: the `starter` commit, whose `make all`
reproduces the tutorial's published table exactly. "After" adds one
feature, `weather_severity_lag_1` (yesterday's weather, encoded
GOOD/MISTY/BAD = 0/1/2), and its rows are `reports/metrics.json`.
`tests/test_report.py` fails if the two ever disagree.

| Model | Features | Valid R² | Valid MAE | Test R² | Test MAE |
|---|---|---:|---:|---:|---:|
| `baseline_mean` | before | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| `baseline_mean` | after | -0.9318 | 2002.2 | -2.1441 | 2847.7 |
| `baseline_persistence` | before | 0.4507 | 900.6 | 0.5099 | 840.1 |
| `baseline_persistence` | after | 0.4507 | 900.6 | 0.5099 | 840.1 |
| `ridge` | before | 0.6475 | 832.9 | 0.5833 | 947.1 |
| `ridge` | after | 0.667 | 803.9 | 0.6124 | 910.6 |
| `hgb` | before | 0.2185 | 1296.6 | -0.4975 | 1972.6 |
| `hgb` | after | 0.2437 | 1275.2 | -0.4687 | 1950.4 |

MAE is in rides per day. The baselines do not move because the feature
drops no extra rows (348/182/184 in both runs). The test rows were first
read after the feature decision was committed.

## Headline finding

**A bare R² is not a finding.** Handing a model every column scores test
R² = 1.000 (`python -m src.leakage_demo`), and that evaluation is invalid,
because `casual + registered = cnt`. Under a temporal split, the mean
baseline scores −2.14 on test, because ridership grew about 65% from 2011
to 2012. Ridge reaches 0.612 against 0.510 for persistence ("yesterday
again"), but loses to it on MAE, 910.6 vs 840.1 rides a day. Gradient
boosting scores −0.469, because a tree cannot predict above the highest
count it was trained on: the 2011 maximum is 6,043, and 104 of the 184
test days (56.5%) exceed it. Adding yesterday's weather raised ridge's
validation R² from 0.6475 to 0.667 and its test R² from 0.5833 to 0.6124
(test MAE 947.1 → 910.6), so I kept it, although ridge still loses to
persistence on MAE.

## Exercise 4: target transformation

**The transformation.** `ratio_roll_7` has the tree predict
`cnt / cnt_roll_7` instead of `cnt`, then multiplies the prediction by
`cnt_roll_7` to get rides back. `cnt_roll_7` is the 7-day mean ending
yesterday. It runs behind a flag (`python -m src.train --target-transform
ratio_roll_7`), and `reports/metrics.json` stays the untransformed
pipeline.

**How it was chosen.** I tried four targets, on validation only:

| Target (validation only) | ridge R² | ridge MAE | hgb R² | hgb MAE |
|---|---:|---:|---:|---:|
| none (`reports/metrics.json`) | 0.667 | 803.9 | 0.2437 | 1275.2 |
| `log` | 0.0354 | 1235.3 | 0.1721 | 1337.8 |
| `diff_lag_1` (cnt − yesterday) | 0.6675 | 802.4 | 0.6254 | 804.3 |
| `diff_roll_7` (cnt − 7-day mean) | 0.6753 | 790.8 | 0.7149 | 729.4 |
| `ratio_roll_7` (cnt ÷ 7-day mean) | 0.4305 | 1044.1 | 0.7591 | 662.0 |

**Why it works.**

- **The failure:** untransformed, the booster never predicted above 5,580
  on validation, below 2011's maximum of 6,043, while 71 of the 182
  validation days exceeded that maximum. Its mean error was −1,178 rides a
  day.
- **The fix:** dividing by a lagged level removes the level from what the
  tree has to learn. What remains is a multiplier for weather, weekday and
  holidays, which applies at any level of demand.
- **The result:** the maximum prediction rose to 8,245, the mean error
  shrank to −280, and MAE on the above-maximum days fell from 1,986 to 668.
- **`log` does not help:** it is monotone, so the tree's predictions are
  still capped at the training maximum.

On validation, the transformed booster beats ridge's best target by
+0.084 R² (paired bootstrap 95% CI +0.028 to +0.142).

**Test, touched once.** I committed the decision, with the pairs to test
fixed in advance, before touching test. Then I ran
`python -m src.train --touch-test hgb:ratio_roll_7 ridge:diff_roll_7 ridge:ratio_roll_7`
once, on 2026-11-23. The result is in `reports/exercise4_test.json`, and
the code refuses a second touch while that file exists.

| Test | R² | MAE |
|---|---:|---:|
| hgb + `ratio_roll_7` | 0.6301 | 833.7 |
| ridge + `diff_roll_7` (ridge's best target) | 0.6191 | 898.2 |
| ridge, untransformed | 0.6124 | 910.6 |
| persistence | 0.5099 | 840.1 |
| ridge + `ratio_roll_7` | 0.0877 | 1432.1 |

**Defensible, with a narrower claim than validation suggests.**

Why it is defensible:

- **No leakage:** the inverse uses only `cnt_roll_7`, which is known at
  prediction time.
- **Chosen without test:** the transformation was picked on validation,
  and the decision was committed before test was touched.
- **It fixes a diagnosed failure:** the gain comes from a mechanism I can
  point to, not from tuning noise.
- **Ridge got the same menu:** it was offered all four targets and its
  best still trailed.

What it does not show:

- **"Trees beat linear models":** the lead over ridge's best target shrank
  from +0.084 on validation to +0.011 on test. The validation bootstrap
  interval for that gap is 0.11 wide, so 0.011 on another half-year is
  within noise. Picking the best of four on validation also flatters the
  validation number, which is why I quote the test number.
- **That it is the same tree:** the transformed model is a 7-day level
  times a learned multiplier, so it borrows persistence's assumption that
  the recent level carries over. It would break at a sudden level change,
  such as a system expansion or a closure.

The honest claim is that a level-relative target makes the tree
competitive with ridge. It is also the only model ahead of persistence on
both test R² and MAE, by 6 rides a day on MAE.

## Exercise 5: ridge vs persistence

Not as it stands. On test, ridge beats persistence on R² (0.6124 vs 0.5099; the starter's gap of 0.07 widened to 0.10 with my feature) and on RMSE (1,084 vs 1,219), but it loses on MAE (910.6 vs 840.1) and on median error (878 vs 507), and it is closer to the truth on only 41% of test days. R² rewards ridge for the 19 days with the largest day-to-day swings (the top 10%), where it misses by 1,793 rides against persistence's 2,909; on the other 165 days it is worse, 809 vs 602. The cause is a level bias: trained on 2011, ridge under-predicts H2 2012 by 523 rides a day on average (persistence: +16), about 9% of an average test day. The same bias was already there on validation (−479), so it is structural, not bad luck in one half-year. For an operator planning bikes and staff, a forecast that is reliably about 9% low on a typical day costs more than "same as yesterday" plus a human override on the few storm and holiday days, which are exactly the days persistence predictably misses. I would deploy persistence, and revisit ridge only once its level bias is fixed (for example by refitting on a rolling window). The model worth testing against persistence next is the level-relative booster from Exercise 4, the only one ahead of it on both test R² (0.630) and MAE (833.7), although its MAE lead is just 6 rides a day.

## Attribution

**Model:** Claude Opus 5.5 (Anthropic, hosted, size not published) in a claude.ai agent workspace, not the course's local `qwen3.5:9b`; no switch, one model for all agent work after the starter commit.

Exception: `reports/audit.jsonl` and the `/leakage-auditor` run in `docs/AUDIT.md` were produced on my machine with `bikeshare-coder` (`qwen3.5:9b`, 64k context) via Ollama.

**(a) Generated by the agent**

- **`src/features.py`:** `weather_severity_lag_1`.
- **`src/config.py`:** `RAW_FEATURE_COLS`, `ENCODED_COLS`, `CALENDAR_COLS`,
  `KEY_COLS`, `CLASSIFIED`, `RAW_SHA256` and `EX4_TEST`.
- **`src/ingest.py`:** `unclassified_columns`, `sha256`, and the hash and
  classification checks in `load_raw`.
- **`src/train.py`:** `TRANSFORMS`, `TargetTransformed`, `exercise4`,
  `_pair` and the `--target-transform` / `--touch-test` flags.
- **`tests/test_leakage.py`:** `test_weather_lag_is_true_calendar_lag`,
  `test_every_target_lag_matches_the_calendar` and
  `test_unmapped_weather_label_fails_loudly`.
- **`tests/test_contract.py`:** `test_every_raw_column_is_classified`,
  `test_a_new_raw_column_is_flagged`,
  `test_raw_columns_reach_the_model_only_if_classified_as_features`,
  `test_each_column_has_exactly_one_reason` and
  `test_tampered_raw_file_is_refused`.
- **`tests/test_report.py`:** the check that this table matches
  `reports/metrics.json`.
- **`.claude/`:** `hooks/guard_raw.sh` and `hooks/stop_gate.sh`; the
  Windows fixes in `hooks/check_leakage.sh`; the new hook entries in
  `settings.json`; and `skills/seed-fault/` (`SKILL.md`, `record.sh`).
- **Repo settings:** `.gitattributes`, and the `.gitignore` change.
- **Docs:** the `CLAUDE.md` edits, `docs/SEEDED_FAULTS.md`, every
  `docs/DECISIONS.md` line after the starter's five, and the first draft
  of this report.
- **Outputs:** `reports/metrics.json` (`make all`) and
  `reports/exercise4_test.json` (`--touch-test`).

**(b) Decisions that were mine.** Items marked *(course)* were fixed by the
starter and the tutorial, and I adopted them. The rest were proposed by the
agent, with the evidence shown in `docs/DECISIONS.md`, and accepted by me
after review. Each item traces to a line there.

- **What to predict:** `cnt` one day ahead, with lags up to d−1 and the
  calendar and observed weather for d treated as known. That last part is
  a perfect-weather-forecast assumption, which I report as a caveat.
  *(course, plus the caveat)* Line "Target".
- **What counts as leakage:** `casual` and `registered` (identity),
  `cnt_2d_bfr` (unverified), and the time indexes *(course)*, starter lines
  1-3. Also, no raw column reaches the model unclassified: line "Every raw
  column must be classified".
- **How to split:** by date, 2011 / H1 2012 / H2 2012. Test is read only
  after the feature work, and once for Exercise 4. *(course)* Starter line
  4 and line "Exercise 4".
- **Which baselines:** mean and persistence beside every score.
  *(course)* Starter line 5.
- **Whether the answer is believable:** the ranking yes, a deployment
  number no. Line "Believability".
- **Whether to keep my feature:** kept, at +0.0195 validation R² (95% CI
  +0.009 to +0.030). Lines "Added `weather_severity_lag_1`" and "Kept".
- **Exercise 4:** `ratio_roll_7` is defensible with the narrower claim.
  Line "Exercise 4".
- **Guarding the raw data and CLAUDE.md:** guard `data/raw/` by its hash,
  and keep `CLAUDE.md` to rules the code cannot show. Lines "`data/raw/` is
  guarded", "`check_leakage.sh`" and "CLAUDE.md".
