# Audit of a teammate's repository (Exercise 3)

- **Repository audited:** https://github.com/brianjjing/DSC-180A-Methodology-6
  at commit `153fddd` ("exercise 1"). The project lives in the repo's
  `bikeshare-open-starter/` folder. At this commit it is the starter plus his
  Exercise 1 feature, `cnt_roll_7_std`, and its test; later commits are not
  covered.
- **How it was run:** Claude Code started in `bikeshare-open-starter/` of a
  fresh clone, with `bikeshare-coder` (`qwen3.5:9b`, 64k context) via Ollama.
  The prompt was:
  `Use the leakage-auditor subagent to audit every change in this repo since its first commit (git diff $(git rev-list --max-parents=0 HEAD) HEAD -- src tests) against its five checks. Print its report exactly as it returns it.`
  Claude Code's auto-mode safety check cannot run against a local model, so I
  approved each action by hand. The subagent ran in the background and
  finished in 1m 13s.

## `/leakage-auditor` output, verbatim

As Claude Code printed it, under "Here's the leakage auditor's report:":

```
  Leakage Auditor Report

  Audited scope: All changes since initial commit (git diff HEAD~1 HEAD for src/ and tests/)

  Five checks evaluated:

  ┌──────────────────┬────────┬────────────────────────────────────────────────────────────────────────────────────┐
  │      Check       │ Status │                                      Details                                       │
  ├──────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Target leakage   │ ✅     │ LEAKAGE_COLS = {"casual", "registered", "cnt"} documented. All lags use .shift(1)  │
  │                  │ Pass   │ before aggregation.                                                                │
  ├──────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Temporal         │ ✅     │ Temporal split: train=2011, valid=H1 2012, test=H2 2012. Models fit on train only. │
  │ ordering         │ Pass   │                                                                                    │
  ├──────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Calendar gaps    │ ✅     │ reindex_to_calendar() fills missing days (e.g., 2011-03-10).                       │
  │                  │ Pass   │                                                                                    │
  ├──────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Silent row loss  │ ✅     │ Only .dropna() removes rows after lag warmup, documented and bounded in tests.     │
  │                  │ Pass   │                                                                                    │
  ├──────────────────┼────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Unreported       │ ✅     │ Both baseline_mean and baseline_persistence fitted alongside ridge/hgb.            │
  │ baseline         │ Pass   │                                                                                    │
  └──────────────────┴────────┴────────────────────────────────────────────────────────────────────────────────────┘

  Diff additions:
  - New feature: cnt_roll_7_std (properly lagged)
  - New validation test for the above feature

  Conclusion: No findings change a number or invalidate a conclusion. All code changes maintain correctness per
  CLAUDE.md rules.
```

## My verdict

I agree with all five passes, and none of them changes a number. The only
code change, `cnt_roll_7_std`, is `out[TARGET].shift(1).rolling(LAG_WARMUP).std()`,
computed after `reindex_to_calendar`. So it uses only days d-7 to d-1, never
reaches across the missing 2011-03-10, and is missing on exactly the rows where
`cnt_roll_7` is, which means no extra rows are dropped. His test pins
2012-03-15 to the sample standard deviation of the seven earlier days, which
matches pandas' default `ddof=1`. Two caveats about the audit itself. It is
loosely worded: it says all lags use `.shift(1)`, but `cnt_lag_7` uses
`.shift(LAG_WARMUP)`, which is also leak-free. And its five checks cannot see
the one thing in this diff that inflates a number: his `docs/DECISIONS.md` says
the feature was the best of 17 candidates screened on validation, so the
reported +0.075 validation R^2 is optimistic. That is a selection effect, not
leakage, and he flags it himself.

## Batch auditor on my own repo

`python agent/audit.py . --out reports/audit.jsonl` (committed with this file),
run on the finished repo, reported `leakage: none`, `temporal_ok: true`,
`baseline_reported: true` and `reproducible: true`, confidence high, with an
empty findings list (`0 flagged`). An earlier run, before the last two fix
commits, also flagged nothing; its five "findings" were notes that checks
passed. Both runs wrote to the repo even though the auditor has no Edit or
Write tool, because its Bash tool can. The second rewrote
`reports/metrics.json` (same numbers), and a stray `temp_features_check.csv`
that appeared in the repo root after the first most likely came from it too. I
restored `reports/metrics.json` and deleted the stray file rather than commit
either.
