-- Does a high VIX month tell you anything about the next 12 months?
with m as (
    select
        month,
        vix_avg,
        fwd_return_12m,
        case
            when vix_avg < 15 then '1. calm (<15)'
            when vix_avg < 20 then '2. normal (15-20)'
            when vix_avg < 30 then '3. elevated (20-30)'
            else                   '4. stress (30+)'
        end as vix_regime
    from {{ ref('fct_market_monthly') }}
    where vix_avg is not null
)

select
    vix_regime,
    count(*)                                                   as months,
    count(fwd_return_12m)                                      as months_with_fwd_data,
    avg(fwd_return_12m)                                        as avg_fwd_return_12m,
    median(fwd_return_12m)                                     as median_fwd_return_12m,
    avg(case when fwd_return_12m > 0 then 1.0 else 0 end)
        filter (where fwd_return_12m is not null)              as pct_positive,
    min(fwd_return_12m)                                        as worst_fwd_return_12m,
    max(fwd_return_12m)                                        as best_fwd_return_12m
from m
group by 1
order by 1
