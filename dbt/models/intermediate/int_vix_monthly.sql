select
    date_trunc('month', trade_date)::date   as month,
    count(*)                                as trading_days,
    avg(vix_close)                          as vix_avg,
    max(vix_high)                           as vix_max,
    arg_max(vix_close, trade_date)          as vix_month_end
from {{ ref('stg_vix_daily') }}
group by 1
