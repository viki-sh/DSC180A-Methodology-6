"""Stage 3: temporal split, fit, evaluate, write metrics.

Two baselines and two models, on purpose.

  baseline_mean         predict the 2011 average for every day
  baseline_persistence  predict yesterday's count (cnt_lag_1)
  ridge                 standardised linear model on the audited features
  hgb                   gradient-boosted trees on the same features

The mean baseline shows what "the distribution moved" costs. Persistence
is the baseline that actually matters: ridge's features are dominated by
lagged demand, so if it cannot beat "yesterday again" it has learned
nothing worth reporting. The booster is there because it fails, and the
reason it fails is the headline result.

Run: python -m src.train
     python -m src.train --target-transform NAME [--touch-test]   (Exercise 4)
"""
import argparse
import datetime
import json

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.config import EX4_TEST, METRICS, PROCESSED, TARGET, TRAIN_END, VALID_END
from src.features import feature_columns


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single lagged column unchanged. Nothing is fit."""

    def __init__(self, column: str = "cnt_lag_1"):
        self.column = column

    def fit(self, X, y=None):
        if self.column not in X.columns:
            raise ValueError(f"persistence baseline needs column {self.column!r}")
        return self

    def predict(self, X):
        return X[self.column].to_numpy(dtype=float)


MODELS = {
    "baseline_mean": DummyRegressor(strategy="mean"),
    "baseline_persistence": PersistenceBaseline("cnt_lag_1"),
    "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "hgb": HistGradientBoostingRegressor(random_state=0, max_iter=300),
}


def temporal_split(df: pd.DataFrame):
    """Split by date, never at random. A random split on a time series
    puts tomorrow in train and today in test."""
    train = df[df.dteday <= TRAIN_END]
    valid = df[(df.dteday > TRAIN_END) & (df.dteday <= VALID_END)]
    test = df[df.dteday > VALID_END]
    return train, valid, test


def fit_and_score() -> dict:
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)

    results = {
        "n_features": len(cols),
        "features": cols,
        "n_train": len(train),
        "n_valid": len(valid),
        "n_test": len(test),
    }
    for name, model in MODELS.items():
        model.fit(train[cols], train[TARGET])
        results[name] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in [("valid", valid), ("test", test)]
        }
    return results


# --- Exercise 4: target transformations, behind a flag -------------------
# The booster fails because most test days exceed every count it saw in
# 2011, and a tree cannot predict outside its training range. These
# transforms make it predict cnt *relative to a lagged level*, then add the
# level back from a column known at prediction time. Nothing here runs
# without --target-transform, and reports/metrics.json is always the
# untransformed pipeline.
TRANSFORMS = {
    "log": (lambda y, X: np.log(y), lambda z, X: np.exp(z)),
    "diff_lag_1": (lambda y, X: y - X["cnt_lag_1"], lambda z, X: z + X["cnt_lag_1"]),
    "diff_roll_7": (lambda y, X: y - X["cnt_roll_7"], lambda z, X: z + X["cnt_roll_7"]),
    "ratio_roll_7": (lambda y, X: y / X["cnt_roll_7"], lambda z, X: z * X["cnt_roll_7"]),
}


class TargetTransformed(BaseEstimator, RegressorMixin):
    """Fit `estimator` on TRANSFORMS[transform] of y; invert on predict."""

    def __init__(self, estimator=None, transform: str = "log"):
        self.estimator = estimator
        self.transform = transform

    def fit(self, X, y):
        forward, _ = TRANSFORMS[self.transform]
        self.estimator_ = clone(self.estimator).fit(X, forward(np.asarray(y, dtype=float), X))
        return self

    def predict(self, X):
        _, inverse = TRANSFORMS[self.transform]
        return np.asarray(inverse(self.estimator_.predict(X), X), dtype=float)


def exercise4(pairs: list[tuple[str, str]], touch_test: bool) -> dict:
    """Score (model, transform) pairs on validation; with touch_test, also on
    test, exactly once: the result goes to EX4_TEST, and a second attempt is
    refused while that file exists."""
    if touch_test and EX4_TEST.exists():
        raise SystemExit(f"{EX4_TEST.name} exists: the Exercise 4 test set was already touched.")
    df = pd.read_parquet(PROCESSED)
    cols = feature_columns(df)
    train, valid, test = temporal_split(df)
    splits = [("valid", valid)] + ([("test", test)] if touch_test else [])
    out = {}
    for name, transform in pairs:
        model = TargetTransformed(MODELS[name], transform).fit(train[cols], train[TARGET])
        out[f"{name}_{transform}"] = {
            split: {
                "r2": round(float(r2_score(part[TARGET], model.predict(part[cols]))), 4),
                "mae": round(float(mean_absolute_error(part[TARGET], model.predict(part[cols]))), 1),
            }
            for split, part in splits
        }
    if touch_test:
        out["test_touched"] = datetime.date.today().isoformat()
        EX4_TEST.write_text(json.dumps(out, indent=2))
    return out


def _pair(text: str) -> tuple[str, str]:
    name, _, transform = text.partition(":")
    if name not in ("ridge", "hgb") or transform not in TRANSFORMS:
        raise argparse.ArgumentTypeError(f"expected ridge|hgb:{'|'.join(sorted(TRANSFORMS))}, got {text!r}")
    return name, transform


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-transform", choices=sorted(TRANSFORMS),
                    help="Exercise 4: validation scores for ridge and hgb under this transform")
    ap.add_argument("--touch-test", nargs="+", type=_pair, metavar="MODEL:TRANSFORM",
                    help="Exercise 4: score these pre-chosen pairs on the test set, once")
    ns = ap.parse_args()
    if ns.touch_test:
        print(json.dumps(exercise4(ns.touch_test, touch_test=True), indent=2))
    elif ns.target_transform:
        t = ns.target_transform
        print(json.dumps(exercise4([("ridge", t), ("hgb", t)], touch_test=False), indent=2))
    else:
        res = fit_and_score()
        METRICS.parent.mkdir(parents=True, exist_ok=True)
        METRICS.write_text(json.dumps(res, indent=2))
        print(json.dumps({k: v for k, v in res.items() if k != "features"}, indent=2))
