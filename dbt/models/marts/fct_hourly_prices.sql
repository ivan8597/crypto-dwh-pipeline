select symbol, hour_ts, avg_price, min_price, max_price, volatility,
       case when prev_hour_price is null or prev_hour_price = 0 then null
            else round((avg_price - prev_hour_price) / prev_hour_price * 100, 2) end as price_change_pct
from {{ ref('int_price_metrics') }}
