"""Basic return and risk metrics for a series of periodic (monthly) returns."""

import numpy as np
import pandas as pd

MONTHS = 12


def _clean(returns) -> pd.Series:
    r = pd.Series(returns, dtype="float64").dropna()
    if r.empty:
        raise ValueError("no returns to work with")
    return r


def annualized_return(returns, periods: int = MONTHS) -> float:
    """Geometric average return per year (CAGR)."""
    r = _clean(returns)
    growth = float(np.prod(1 + r))
    return growth ** (periods / len(r)) - 1


def annualized_volatility(returns, periods: int = MONTHS) -> float:
    r = _clean(returns)
    return float(r.std(ddof=1) * np.sqrt(periods))


def sharpe_ratio(returns, risk_free=0.0, periods: int = MONTHS) -> float:
    """Annualized Sharpe ratio. risk_free is per period (scalar or series)."""
    r = _clean(returns)
    rf = pd.Series(risk_free, index=r.index) if np.isscalar(risk_free) else pd.Series(risk_free).reindex(r.index)
    excess = (r - rf).dropna()
    return float(excess.mean() / excess.std(ddof=1) * np.sqrt(periods))


def sortino_ratio(returns, risk_free=0.0, periods: int = MONTHS) -> float:
    """Like Sharpe but only penalizes downside moves."""
    r = _clean(returns)
    excess = r - risk_free
    downside = np.sqrt(np.mean(np.minimum(excess, 0) ** 2))
    if downside == 0:
        return float("inf")
    return float(excess.mean() / downside * np.sqrt(periods))


def drawdown_series(returns) -> pd.Series:
    """Percent below the running peak of the growth index."""
    r = _clean(returns)
    index = (1 + r).cumprod()
    return index / index.cummax() - 1


def max_drawdown(returns) -> float:
    return float(drawdown_series(returns).min())


def var_historical(returns, level: float = 0.95) -> float:
    """Historical Value at Risk, reported as a positive loss (0.05 = 5%)."""
    r = _clean(returns)
    return float(-np.percentile(r, (1 - level) * 100))


def cvar_historical(returns, level: float = 0.95) -> float:
    """Expected shortfall: average loss in the worst (1 - level) of periods."""
    r = _clean(returns)
    cutoff = np.percentile(r, (1 - level) * 100)
    return float(-r[r <= cutoff].mean())


def summary(returns, risk_free=0.0) -> dict:
    return {
        "cagr": annualized_return(returns),
        "volatility": annualized_volatility(returns),
        "sharpe": sharpe_ratio(returns, risk_free),
        "sortino": sortino_ratio(returns, risk_free),
        "max_drawdown": max_drawdown(returns),
        "var_95": var_historical(returns, 0.95),
        "cvar_95": cvar_historical(returns, 0.95),
    }
