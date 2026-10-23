import numpy as np
import pandas as pd
import pytest

from riskkit import (
    annualized_return,
    annualized_volatility,
    cvar_historical,
    max_drawdown,
    sharpe_ratio,
    var_historical,
)


def test_cagr_of_constant_return():
    # 1% a month for 12 months is 12.68% a year
    r = [0.01] * 12
    assert annualized_return(r) == pytest.approx(1.01**12 - 1)


def test_cagr_ignores_missing_values():
    assert annualized_return([0.01, None, 0.01]) == pytest.approx(1.01**12 - 1)


def test_volatility_of_constant_return_is_zero():
    assert annualized_volatility([0.02] * 24) == pytest.approx(0.0)


def test_max_drawdown_known_path():
    # up 10%, down 50%, up 20% -> index 1.1, 0.55, 0.66 -> worst is -50%
    assert max_drawdown([0.10, -0.50, 0.20]) == pytest.approx(-0.5)


def test_no_drawdown_when_always_rising():
    assert max_drawdown([0.01, 0.02, 0.03]) == pytest.approx(0.0)


def test_var_and_cvar_on_simple_sample():
    r = pd.Series(np.arange(-10, 10) / 100)  # -10% ... +9%
    var = var_historical(r, 0.90)
    cvar = cvar_historical(r, 0.90)
    assert var > 0
    assert cvar >= var  # average of the tail is at least as bad as the cutoff


def test_sharpe_sign_follows_excess_return():
    rng = np.random.default_rng(0)
    r = pd.Series(rng.normal(0.01, 0.04, 240))
    assert sharpe_ratio(r, 0.0) > 0
    assert sharpe_ratio(r, 0.05) < 0


def test_empty_series_raises():
    with pytest.raises(ValueError):
        annualized_return([])
