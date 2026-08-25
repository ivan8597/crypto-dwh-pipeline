with aggregated as (
    select symbol, hour_ts, avg(price) as avg_price, min(price) as min_price,
           max(price) as max_price, max(price) - min(price) as volatility
    from {{ ref('stg_crypto_prices') }} group by symbol, hour_ts
)
select *, lag(avg_price) over (partition by symbol order by hour_ts) as prev_hour_price
from aggregated
