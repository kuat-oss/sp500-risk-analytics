-- One row per month with price, dividends, inflation and rates combined.
-- Gaps in Shiller's file are filled from the BLS CPI and Treasury files,
-- and the last published dividend is carried forward (and flagged).
with sp as (
    select * from {{ ref('stg_sp500_monthly') }}
),

joined as (
    select
        sp.month,
        sp.sp500_price,
        sp.dividend_ttm,
        sp.earnings_ttm,
        coalesce(sp.cpi_shiller, cpi.cpi)                 as cpi,
        sp.cpi_shiller is null and cpi.cpi is not null    as is_cpi_from_bls,
        coalesce(sp.long_rate_shiller, t.yield_10y)       as yield_10y,
        sp.cape_shiller,
        cpi.cpi                                           as cpi_bls
    from sp
    left join {{ ref('stg_cpi_monthly') }} cpi using (month)
    left join {{ ref('stg_treasury_10y_monthly') }} t using (month)
),

filled as (
    select
        *,
        last_value(dividend_ttm ignore nulls) over (order by month
            rows between unbounded preceding and current row)  as dividend_ttm_filled
    from joined
)

select
    month,
    sp500_price,
    dividend_ttm_filled                                      as dividend_ttm,
    dividend_ttm is null                                     as is_dividend_estimated,
    earnings_ttm,
    cpi,
    cpi_bls,
    is_cpi_from_bls,
    yield_10y,
    cape_shiller,
    -- price return + one month of the trailing dividend
    sp500_price / lag(sp500_price) over (order by month) - 1                  as price_return,
    (dividend_ttm_filled / 12) / lag(sp500_price) over (order by month)        as dividend_return,
    (sp500_price + dividend_ttm_filled / 12)
        / lag(sp500_price) over (order by month) - 1                           as total_return,
    cpi / lag(cpi) over (order by month) - 1                                   as inflation
from filled
