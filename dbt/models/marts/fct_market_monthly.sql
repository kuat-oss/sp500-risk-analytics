-- Main monthly fact table used by the app and the Python analysis.
with base as (
    select
        m.*,
        (1 + m.total_return) / (1 + m.inflation) - 1   as real_total_return,
        v.vix_avg,
        v.vix_max
    from {{ ref('int_market_monthly') }} m
    left join {{ ref('int_vix_monthly') }} v using (month)
),

indexed as (
    select
        *,
        -- growth of $1 invested in Jan 1871 (dividends reinvested)
        exp(sum(ln(1 + coalesce(total_return, 0))) over w)        as tr_index,
        case when inflation is not null or month = (select min(month) from base)
             then exp(sum(ln(1 + coalesce(real_total_return, 0))) over w)
        end                                                        as real_tr_index,
        -- my own CAPE: price / 10 year average of inflation adjusted earnings
        case when count(earnings_ttm / cpi) over w120 = 120
             then (sp500_price / cpi) / avg(earnings_ttm / cpi) over w120
        end                                                        as cape_calc
    from base
    window
        w    as (order by month rows between unbounded preceding and current row),
        w120 as (order by month rows between 119 preceding and current row)
)

select
    month,
    extract(year from month)::int                                   as year,
    sp500_price,
    dividend_ttm,
    is_dividend_estimated,
    earnings_ttm,
    cpi,
    is_cpi_from_bls,
    yield_10y,
    price_return,
    dividend_return,
    total_return,
    inflation,
    real_total_return,
    tr_index,
    real_tr_index,
    tr_index / max(tr_index) over w - 1                             as drawdown,
    real_tr_index / max(real_tr_index) over w - 1                   as real_drawdown,
    tr_index / lag(tr_index, 12) over (order by month) - 1          as return_12m,
    stddev_samp(total_return) over w36 * sqrt(12)                   as vol_36m,
    cape_shiller,
    cape_calc,
    1 / cape_calc                                                   as cape_earnings_yield,
    dividend_ttm / sp500_price                                      as dividend_yield,
    vix_avg,
    vix_max,
    -- what happened next (null for the most recent months)
    tr_index_fwd_12m / tr_index - 1                                 as fwd_return_12m,
    power(real_tr_index_fwd_120m / real_tr_index, 1.0 / 10) - 1     as fwd_real_cagr_10y
from (
    select
        *,
        lead(tr_index, 12) over (order by month)        as tr_index_fwd_12m,
        lead(real_tr_index, 120) over (order by month)  as real_tr_index_fwd_120m
    from indexed
)
window
    w   as (order by month rows between unbounded preceding and current row),
    w36 as (order by month rows between 35 preceding and current row)
