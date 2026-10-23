"""Monte Carlo of a monthly investing plan using block bootstrap of history.

Sampling 12-month blocks instead of single months keeps some of the
momentum / mean reversion in real data, which plain random draws lose.
"""

import numpy as np
import pandas as pd


def bootstrap_paths(returns, months: int, n_paths: int = 5000, block: int = 12, seed: int = 42) -> np.ndarray:
    r = pd.Series(returns, dtype="float64").dropna().to_numpy()
    if len(r) < block:
        raise ValueError("not enough history for one block")
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(months / block))
    starts = rng.integers(0, len(r) - block + 1, size=(n_paths, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_paths, -1)[:, :months]
    return r[idx]


def simulate_plan(returns, years: int, monthly_contribution: float, initial: float = 0.0,
                  n_paths: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Ending value of each path for a plan that adds money at the start of each month."""
    months = years * 12
    paths = bootstrap_paths(returns, months, n_paths=n_paths, seed=seed)
    value = np.full(n_paths, float(initial))
    for m in range(months):
        value = (value + monthly_contribution) * (1 + paths[:, m])
    invested = initial + monthly_contribution * months
    return pd.DataFrame({"ending_value": value, "invested": invested})


def plan_percentiles(sim: pd.DataFrame, pct=(5, 25, 50, 75, 95)) -> dict:
    return {p: float(np.percentile(sim["ending_value"], p)) for p in pct}
