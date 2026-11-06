"""Shape matching: Pearson r between a target series and candidate profiles."""
from __future__ import annotations

import numpy as np
import pandas as pd


def zscore_rows(a: np.ndarray) -> np.ndarray:
    a = np.atleast_2d(np.asarray(a, float))
    sd = a.std(axis=1, keepdims=True)
    sd[sd == 0] = np.nan
    return (a - a.mean(axis=1, keepdims=True)) / sd


def pearson_rows(cands: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """r for every (candidate, target) pair → shape [n_cand, n_target]."""
    zc, zt = zscore_rows(cands), zscore_rows(targets)
    return zc @ zt.T / zc.shape[1]


def target_series(csv_path, start: str, end: str, n_out: int, kinds=("month", "session")) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Linearly interpolate reported closes onto a uniform calendar grid of ``n_out`` points."""
    df = pd.read_csv(csv_path, parse_dates=["date"])
    df = df[df["kind"].isin(kinds)].sort_values("date")
    if not df["date"].is_monotonic_increasing or df["date"].duplicated().any():
        raise ValueError("dates must be unique and sorted")
    df = df[(df["date"] >= start) & (df["date"] <= end)]
    if df["date"].min() != pd.Timestamp(start) or df["date"].max() != pd.Timestamp(end):
        raise ValueError("start/end must be reported closes")
    t = pd.date_range(start, end, periods=n_out)
    as_ns = lambda x: np.asarray(x, dtype="datetime64[ns]").astype("int64")  # noqa: E731
    v = np.interp(as_ns(t), as_ns(df["date"]), df["close"].to_numpy())
    return t, v


def random_walks(n: int, length: int, rng: np.random.Generator) -> np.ndarray:
    """Gaussian random walks; shape is all that matters (Pearson r is scale-free)."""
    return np.cumsum(rng.standard_normal((n, length)), axis=1)
