-- Every fall of 20% or more from a previous high (total return, nominal).
-- Classic gaps-and-islands: each new high starts a new group.
with m as (
    select
        month,
        tr_index,
        drawdown,
        sum(case when drawdown = 0 then 1 else 0 end)
            over (order by month rows between unbounded preceding and current row) as grp
    from {{ ref('fct_market_monthly') }}
),

episodes as (
    select
        grp,
        min(month)                        as peak_month,
        arg_min(month, drawdown)          as trough_month,
        min(drawdown)                     as max_drawdown,
        count(*) - 1                      as months_under_water
    from m
    group by grp
),

next_high as (
    select grp, min(month) as recovery_month
    from m
    where drawdown = 0
    group by grp
)

select
    row_number() over (order by e.peak_month)                    as episode_id,
    e.peak_month,
    e.trough_month,
    n.recovery_month,
    round(e.max_drawdown, 4)                                     as max_drawdown,
    date_diff('month', e.peak_month, e.trough_month)             as months_peak_to_trough,
    date_diff('month', e.trough_month, n.recovery_month)         as months_trough_to_recovery,
    n.recovery_month is null                                     as is_ongoing
from episodes e
left join next_high n on n.grp = e.grp + 1
where e.max_drawdown <= -0.20
