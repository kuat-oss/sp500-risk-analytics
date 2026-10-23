"""Does a high CAPE predict lower returns over the next 10 years?"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass
class CapeModel:
    intercept: float
    slope: float
    r_squared: float
    slope_t_stat: float
    observations: int

    def predict(self, cape: float) -> float:
        return self.intercept + self.slope * np.log(cape)


def fit_cape_model(df: pd.DataFrame) -> CapeModel:
    """OLS of next-10y real CAGR on log(CAPE).

    The 10 year windows overlap month to month, so plain standard errors are
    far too optimistic. I use Newey-West (HAC) errors with a 120 month lag.
    """
    data = df[["cape_calc", "fwd_real_cagr_10y"]].dropna()
    x = sm.add_constant(np.log(data["cape_calc"]))
    fit = sm.OLS(data["fwd_real_cagr_10y"], x).fit(cov_type="HAC", cov_kwds={"maxlags": 120})
    return CapeModel(
        intercept=float(fit.params.iloc[0]),
        slope=float(fit.params.iloc[1]),
        r_squared=float(fit.rsquared),
        slope_t_stat=float(fit.tvalues.iloc[1]),
        observations=int(fit.nobs),
    )


def cape_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Average next-10y real return by CAPE range."""
    data = df[["cape_calc", "fwd_real_cagr_10y"]].dropna()
    bins = [0, 10, 15, 20, 25, 30, np.inf]
    labels = ["<10", "10-15", "15-20", "20-25", "25-30", "30+"]
    data = data.assign(cape_range=pd.cut(data["cape_calc"], bins=bins, labels=labels))
    out = data.groupby("cape_range", observed=True)["fwd_real_cagr_10y"].agg(
        months="count", avg="mean", worst="min", best="max"
    )
    return out.reset_index()
