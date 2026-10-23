select
    cast("Date" as date)   as month,
    "Rate"                 as yield_10y
from {{ source('raw', 'treasury_10y_monthly') }}
where "Rate" is not null
