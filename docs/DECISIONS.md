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
