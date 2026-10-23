-- Shiller's CPI and the BLS file should be the same series where both exist
select month, cpi, cpi_bls
from {{ ref('int_market_monthly') }}
where cpi_bls is not null
  and not is_cpi_from_bls
  and abs(cpi / cpi_bls - 1) > 0.01
