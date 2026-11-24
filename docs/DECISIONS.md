# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- 2026-11-23: Added `weather_severity_lag_1` (yesterday's encoded weather). Availability: d-1's weather is observed by the end of d-1; it is shifted on the calendar grid, so the day after 2011-03-10 is NaN and dropped, never 03-09's weather. Validation R^2: ridge 0.6475 -> 0.6670 (+0.0195, paired-bootstrap 95% CI +0.009 to +0.030), hgb 0.2185 -> 0.2437 (+0.0252); ridge MAE 832.9 -> 803.9. Rows unchanged (348/182/184), so the baselines are unchanged.
- 2026-11-23: Kept `weather_severity_lag_1`. The gain clears the 0.01 noise bar and the mechanism was checked on train only (2011: the day after a BAD day averages +785 rides over yesterday). The validation gain is concentrated on the 57 days after MISTY weather; only 2 validation days follow a BAD day.
- 2026-11-23: Every raw column must be classified in `src/config.py` (FORBIDDEN, or RAW_FEATURE / ENCODED / CALENDAR / KEY). `load_raw` refuses unclassified columns and `tests/test_contract.py` checks it. Reason: `feature_columns()` admits any numeric column not in FORBIDDEN, so a new same-day column in the CSV would become a feature without anyone deciding. That is the one leak `test_no_forbidden_features` cannot see. Metrics unchanged.
- 2026-11-23: Exercise 4: target transform `ratio_roll_7` for hgb (predict cnt / cnt_roll_7, multiply back), behind `--target-transform`; `reports/metrics.json` stays untransformed. Chosen on validation from four candidates (log, diff_lag_1, diff_roll_7, ratio_roll_7): hgb valid R^2 0.2437 -> 0.7591, MAE 1275.2 -> 662.0, versus 0.6753 for ridge's best transform (diff_roll_7). Judged defensible before test was touched. The level is lagged, so it is known at prediction time. The transform fixes a diagnosed failure: untransformed hgb never predicts above 5,580, under the 2011 max of 6,043, while 71 of 182 validation days exceed it. Ridge was offered the same menu. Test touched once afterwards, for pairs fixed in advance: hgb:ratio_roll_7, ridge:diff_roll_7, ridge:ratio_roll_7.
