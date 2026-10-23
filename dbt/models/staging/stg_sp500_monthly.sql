-- Shiller's file uses 0 for "not published yet" (recent months have no
-- dividends/earnings/cpi), so turn those into nulls instead of real zeros.
select
    cast("Date" as date)                         as month,
    "SP500"                                      as sp500_price,
    nullif("Dividend", 0)                        as dividend_ttm,
    nullif("Earnings", 0)                        as earnings_ttm,
    nullif("Consumer Price Index", 0)            as cpi_shiller,
    nullif("Long Interest Rate", 0)              as long_rate_shiller,
    nullif("Real Price", 0)                      as real_price_shiller,
    nullif("Real Earnings", 0)                   as real_earnings_shiller,
    nullif("PE10", 0)                            as cape_shiller
from {{ source('raw', 'sp500_monthly') }}
