select
    "Symbol"                     as symbol,
    "Security"                   as company,
    "GICS Sector"                as sector,
    "GICS Sub-Industry"          as sub_industry,
    "Headquarters Location"      as headquarters,
    cast("Date added" as date)   as date_added,
    "CIK"                        as cik,
    -- a few rows have values like "1902 (1880)", keep the first year
    try_cast(left(trim("Founded"), 4) as integer) as founded_year
from {{ source('raw', 'sp500_constituents') }}
