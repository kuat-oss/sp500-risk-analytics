-- When did today's S&P 500 members join the index, by sector?
select
    decade_added,
    sector,
    count(*) as companies
from {{ ref('dim_constituents') }}
group by 1, 2
order by 1, 2
