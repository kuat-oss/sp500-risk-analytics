select
    cast("Date" as date)   as month,
    "Index"                as cpi
from {{ source('raw', 'cpi_monthly') }}
where "Index" is not null
