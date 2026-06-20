-- int_fundamental_daily: join fundamentals to daily price

select
    p.symbol_key,
    p.trade_date,

    f.roe as roe_ttm,

    case
        when f.equity is not null and f.equity <> 0
        then f.total_liabilities / f.equity
        else null
    end as debt_to_equity

from {{ ref('int_price_daily') }} p

left join lateral (
    select *
    from {{ ref('int_fundamental_pivot') }} f
    where f.symbol_key = p.symbol_key
      and f.period_end_date <= p.trade_date
    order by f.period_end_date desc
    limit 1
) f on true
