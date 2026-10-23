select
    *,
    (extract(year from date_added)::int // 10) * 10   as decade_added,
    date_diff('year', date_added, current_date)        as years_in_index
from {{ ref('stg_sp500_constituents') }}
