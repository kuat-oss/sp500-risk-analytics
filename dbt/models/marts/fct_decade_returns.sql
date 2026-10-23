select
    (year // 10) * 10                                                    as decade,
    count(*)                                                             as months,
    count(*) < 120                                                       as is_partial,
    exp(sum(ln(1 + total_return)) * 12 / count(total_return)) - 1        as cagr,
    exp(sum(ln(1 + real_total_return)) * 12 / count(real_total_return)) - 1 as real_cagr,
    stddev_samp(total_return) * sqrt(12)                                 as volatility,
    min(total_return)                                                    as worst_month,
    arg_min(month, total_return)                                         as worst_month_date,
    avg(inflation) * 12                                                  as avg_inflation
from {{ ref('fct_market_monthly') }}
where total_return is not null
group by 1
order by 1
