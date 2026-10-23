import numpy as np
import pandas as pd
import pytest

from riskkit.simulation import bootstrap_paths, plan_percentiles, simulate_plan
from riskkit.valuation import cape_buckets, fit_cape_model


def fake_market(n=600, seed=1):
    rng = np.random.default_rng(seed)
    cape = rng.uniform(8, 40, n)
    fwd = 0.25 - 0.06 * np.log(cape) + rng.normal(0, 0.01, n)
    return pd.DataFrame({"cape_calc": cape, "fwd_real_cagr_10y": fwd})


def test_cape_model_recovers_negative_slope():
    model = fit_cape_model(fake_market())
    assert model.slope == pytest.approx(-0.06, abs=0.01)
    assert model.predict(40) < model.predict(10)


def test_cape_buckets_cover_all_rows():
    df = fake_market()
    out = cape_buckets(df)
    assert out["months"].sum() == len(df)


def test_bootstrap_shape_and_values_come_from_history():
    hist = np.array([0.01, 0.02, -0.03, 0.04, 0.0, 0.05] * 4)
    paths = bootstrap_paths(hist, months=30, n_paths=50, block=6)
    assert paths.shape == (50, 30)
    assert set(np.unique(paths)).issubset(set(hist))


def test_plan_with_zero_returns_equals_money_put_in():
    sim = simulate_plan([0.0] * 60, years=5, monthly_contribution=100, initial=1000, n_paths=10)
    assert np.allclose(sim["ending_value"], 1000 + 100 * 60)


def test_percentiles_are_ordered():
    rng = np.random.default_rng(3)
    sim = simulate_plan(rng.normal(0.007, 0.04, 600), years=10, monthly_contribution=500, n_paths=500)
    p = plan_percentiles(sim)
    assert p[5] <= p[50] <= p[95]
