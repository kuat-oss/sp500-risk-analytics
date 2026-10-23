-- the monthly series should have no holes
select month, next_month
from (
    select month, lead(month) over (order by month) as next_month
    from {{ ref('fct_market_monthly') }}
)
where next_month is not null
  and next_month <> month + interval 1 month
