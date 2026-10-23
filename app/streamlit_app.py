import os
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from riskkit import drawdown_series, summary
from riskkit.simulation import plan_percentiles, simulate_plan
from riskkit.valuation import cape_buckets, fit_cape_model

WAREHOUSE = ROOT / "warehouse" / "market.duckdb"
BLUE, ORANGE, RED, GREY = "#2a6fdb", "#e8833a", "#c8423b", "#8a8f98"

st.set_page_config(page_title="S&P 500 Risk Analytics", layout="wide")


def build_warehouse():
    """Run dbt if the database isn't there yet (first start on a new machine)."""
    from dbt.cli.main import dbtRunner

    WAREHOUSE.parent.mkdir(exist_ok=True)
    # dbt paths (database + raw csv files) are relative to the dbt folder
    os.environ["WAREHOUSE_PATH"] = str(WAREHOUSE)
    cwd = os.getcwd()
    os.chdir(ROOT / "dbt")
    try:
        res = dbtRunner().invoke(["build", "--profiles-dir", ".", "--quiet"])
    finally:
        os.chdir(cwd)
    if not res.success:
        st.error("dbt build failed, check the logs")
        st.stop()


@st.cache_data
def load():
    if not WAREHOUSE.exists():
        build_warehouse()
    con = duckdb.connect(str(WAREHOUSE))
    tables = {
        name: con.sql(f"select * from {name}").df()
        for name in ["fct_market_monthly", "fct_drawdown_episodes", "fct_decade_returns",
                     "fct_vix_regimes", "dim_constituents", "fct_index_additions"]
    }
    con.close()
    tables["fct_market_monthly"]["month"] = pd.to_datetime(tables["fct_market_monthly"]["month"])
    return tables


data = load()
mkt = data["fct_market_monthly"].set_index("month")
last_month = mkt.index.max()

st.title("S&P 500 risk and return, 1871 to today")
st.caption(
    f"Monthly data from Jan 1871 to {last_month:%b %Y}. Total return = price + reinvested dividends. "
    "Sources: Robert Shiller (S&P 500, earnings, dividends), BLS (CPI), US Treasury (10y yield), CBOE (VIX)."
)

tab_overview, tab_dd, tab_val, tab_vix, tab_sim, tab_members = st.tabs(
    ["Overview", "Drawdowns", "Valuation (CAPE)", "Volatility (VIX)", "Investing simulator", "Index members"]
)

# ---------------- overview ----------------
with tab_overview:
    years = mkt.index.year
    start, end = st.select_slider(
        "Period", options=list(range(years.min(), years.max() + 1)), value=(1990, int(years.max()))
    )
    period = mkt.loc[f"{start}":f"{end}"]
    rf = (period["yield_10y"] / 100 / 12).ffill()
    stats = summary(period["total_return"], rf)
    real_cagr = summary(period["real_total_return"])["cagr"]

    cols = st.columns(6)
    cols[0].metric("CAGR", f"{stats['cagr']:.1%}")
    cols[1].metric("Real CAGR", f"{real_cagr:.1%}")
    cols[2].metric("Volatility", f"{stats['volatility']:.1%}")
    cols[3].metric("Sharpe (vs 10y UST)", f"{stats['sharpe']:.2f}")
    cols[4].metric("Max drawdown", f"{stats['max_drawdown']:.0%}")
    cols[5].metric("Monthly VaR 95%", f"{stats['var_95']:.1%}", help="Historical: 1 month in 20 was worse than this")

    growth = pd.DataFrame({
        "Nominal": (1 + period["total_return"].fillna(0)).cumprod(),
        "Real (after inflation)": (1 + period["real_total_return"].fillna(0)).cumprod(),
    })
    fig = px.line(growth, log_y=True, color_discrete_sequence=[BLUE, ORANGE],
                  labels={"value": "Growth of $1 (log scale)", "month": "", "variable": ""})
    fig.update_layout(height=420, legend=dict(orientation="h", y=1.08), margin=dict(t=30))
    st.plotly_chart(fig, width="stretch")

    st.subheader("Returns by decade")
    dec = data["fct_decade_returns"].copy()
    dec["label"] = dec["decade"].astype(str) + "s" + np.where(dec["is_partial"], "*", "")
    fig = go.Figure()
    fig.add_bar(x=dec["label"], y=dec["cagr"], name="Nominal", marker_color=BLUE)
    fig.add_bar(x=dec["label"], y=dec["real_cagr"], name="Real", marker_color=ORANGE)
    fig.update_layout(barmode="group", yaxis_tickformat=".0%", height=360, margin=dict(t=20),
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch")
    st.caption("* decade not finished yet")

# ---------------- drawdowns ----------------
with tab_dd:
    st.markdown("How far below the previous high the market was, month by month (total return, nominal).")
    dd = drawdown_series(mkt["total_return"].fillna(0))
    fig = px.area(dd, labels={"value": "Drawdown", "month": ""}, color_discrete_sequence=[RED])
    fig.update_layout(yaxis_tickformat=".0%", showlegend=False, height=380, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

    ep = data["fct_drawdown_episodes"].copy()
    ep["total_months"] = ep["months_peak_to_trough"] + ep["months_trough_to_recovery"]
    for col in ["peak_month", "trough_month", "recovery_month"]:
        ep[col] = pd.to_datetime(ep[col]).dt.strftime("%b %Y").fillna("not yet")
    st.subheader("Every fall of 20% or more")
    st.dataframe(
        ep[["peak_month", "trough_month", "recovery_month", "max_drawdown",
            "months_peak_to_trough", "months_trough_to_recovery", "total_months"]]
        .rename(columns={"peak_month": "peak", "trough_month": "bottom", "recovery_month": "back to peak",
                         "max_drawdown": "fall", "months_peak_to_trough": "months falling",
                         "months_trough_to_recovery": "months recovering", "total_months": "total months"})
        .style.format({"fall": "{:.1%}"}),
        hide_index=True, width="stretch",
    )
    st.caption("Based on monthly average prices, so short crashes like Feb-Mar 2020 look smaller than on daily data.")

# ---------------- valuation ----------------
with tab_val:
    model = fit_cape_model(mkt)
    last_cape_month = mkt["cape_calc"].dropna().index.max()
    last_cape = mkt.loc[last_cape_month, "cape_calc"]

    c1, c2, c3 = st.columns(3)
    c1.metric(f"CAPE ({last_cape_month:%b %Y}, last with earnings)", f"{last_cape:.1f}")
    c2.metric("Long-run median CAPE", f"{mkt['cape_calc'].median():.1f}")
    c3.metric("Model: next 10y real return", f"{model.predict(last_cape):.1%} / yr")

    fig = px.line(mkt["cape_calc"].dropna(), labels={"value": "CAPE", "month": ""},
                  color_discrete_sequence=[BLUE])
    fig.add_hline(y=mkt["cape_calc"].median(), line_dash="dash", line_color=GREY,
                  annotation_text="median")
    fig.update_layout(showlegend=False, height=330, margin=dict(t=20))
    st.plotly_chart(fig, width="stretch")

    left, right = st.columns([3, 2])
    with left:
        pts = mkt[["cape_calc", "fwd_real_cagr_10y"]].dropna().reset_index()
        fig = px.scatter(pts, x="cape_calc", y="fwd_real_cagr_10y", opacity=0.35, hover_data=["month"],
                         color_discrete_sequence=[BLUE],
                         labels={"cape_calc": "CAPE at start",
                                 "fwd_real_cagr_10y": "Real return per year, next 10 years"})
        xs = np.linspace(pts["cape_calc"].min(), pts["cape_calc"].max(), 100)
        fig.add_scatter(x=xs, y=[model.predict(x) for x in xs], mode="lines", name="fit",
                        line=dict(color=RED, width=3))
        fig.update_layout(yaxis_tickformat=".0%", showlegend=False, height=420)
        st.plotly_chart(fig, width="stretch")
    with right:
        st.markdown(
            f"**Regression:** next 10y real return = {model.intercept:.3f} {model.slope:+.3f} x ln(CAPE)  \n"
            f"R² = {model.r_squared:.2f}, t-stat on slope = {model.slope_t_stat:.1f} "
            f"(Newey-West, {model.observations} months)"
        )
        b = cape_buckets(mkt)
        st.dataframe(b.style.format({"avg": "{:.1%}", "worst": "{:.1%}", "best": "{:.1%}"}),
                     hide_index=True, width="stretch")
        st.caption("Overlapping 10 year windows, so neighbouring months are not independent.")

# ---------------- vix ----------------
with tab_vix:
    v = mkt.loc["1990":, ["vix_avg", "drawdown"]].dropna()
    fig = go.Figure()
    fig.add_scatter(x=v.index, y=v["vix_avg"], name="VIX (monthly avg)", line=dict(color=ORANGE))
    fig.add_scatter(x=v.index, y=v["drawdown"] * 100, name="Drawdown, %", yaxis="y2",
                    fill="tozeroy", line=dict(color=RED, width=0.5), opacity=0.4)
    fig.update_layout(height=380, margin=dict(t=20), legend=dict(orientation="h", y=1.1),
                      yaxis=dict(title="VIX"), yaxis2=dict(title="Drawdown %", overlaying="y", side="right"))
    st.plotly_chart(fig, width="stretch")

    st.subheader("What happened in the 12 months after each VIX level")
    reg = data["fct_vix_regimes"]
    st.dataframe(
        reg.style.format({c: "{:.1%}" for c in reg.columns if "return" in c or c == "pct_positive"}),
        hide_index=True, width="stretch",
    )

# ---------------- simulator ----------------
with tab_sim:
    st.markdown(
        "Invest a fixed amount every month. Each simulated path is built from random 12 month blocks "
        "of real (after inflation) S&P 500 history, so results are in today's dollars."
    )
    a, b, c = st.columns(3)
    monthly = a.number_input("Monthly contribution ($)", 50, 10000, 500, step=50)
    years_sim = b.slider("Years", 5, 40, 30)
    initial = c.number_input("Starting amount ($)", 0, 1_000_000, 0, step=1000)

    sim = simulate_plan(mkt["real_total_return"].dropna(), years_sim, monthly, initial, n_paths=5000)
    p = plan_percentiles(sim)
    invested = sim["invested"].iloc[0]
    k = st.columns(4)
    k[0].metric("Money put in", f"${invested:,.0f}")
    k[1].metric("Median outcome", f"${p[50]:,.0f}")
    k[2].metric("Bad case (5th pct)", f"${p[5]:,.0f}")
    k[3].metric("Chance of ending below what you put in", f"{(sim['ending_value'] < invested).mean():.1%}")

    cap = np.percentile(sim["ending_value"], 99)  # long right tail squashes the chart
    fig = px.histogram(sim[sim["ending_value"] <= cap], x="ending_value", nbins=80, color_discrete_sequence=[BLUE],
                       labels={"ending_value": "Ending value (today's dollars)"})
    fig.add_vline(x=invested, line_dash="dash", line_color=RED, annotation_text="put in")
    fig.add_vline(x=p[50], line_dash="dash", line_color=GREY, annotation_text="median")
    fig.update_layout(height=380, margin=dict(t=20), yaxis_title="Simulated paths")
    st.plotly_chart(fig, width="stretch")
    st.caption("Top 1% of paths hidden from the chart. Past returns, no fees or taxes. Not investment advice.")

# ---------------- members ----------------
with tab_members:
    members = data["dim_constituents"]
    col_a, col_b = st.columns(2)
    with col_a:
        s = members["sector"].value_counts().sort_values()
        fig = px.bar(s, orientation="h", color_discrete_sequence=[BLUE], labels={"value": "Companies", "sector": ""})
        fig.update_layout(showlegend=False, height=420, title="Current members by sector")
        st.plotly_chart(fig, width="stretch")
    with col_b:
        add = data["fct_index_additions"]
        fig = px.bar(add, x="decade_added", y="companies", color="sector",
                     labels={"decade_added": "Decade added to the index", "companies": "Companies"})
        fig.update_layout(height=420, title="When today's members joined")
        st.plotly_chart(fig, width="stretch")
    recent = (pd.to_datetime(members["date_added"]) >= pd.Timestamp(last_month) - pd.DateOffset(years=10)).mean()
    st.markdown(f"**{recent:.0%}** of today's members were added in the last 10 years.")
