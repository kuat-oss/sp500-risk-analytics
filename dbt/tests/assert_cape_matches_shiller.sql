-- my CAPE calculation should be within 3% of Shiller's published PE10
select month, cape_calc, cape_shiller
from {{ ref('fct_market_monthly') }}
where cape_calc is not null
  and cape_shiller is not null
  and abs(cape_calc / cape_shiller - 1) > 0.03
