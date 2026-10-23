select
    cast("DATE" as date)   as trade_date,
    "OPEN"                 as vix_open,
    "HIGH"                 as vix_high,
    "LOW"                  as vix_low,
    "CLOSE"                as vix_close
from {{ source('raw', 'vix_daily') }}
where "CLOSE" is not null
