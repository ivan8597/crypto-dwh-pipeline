select * from {{ ref('fct_hourly_prices') }} where abs(price_change_pct) > 50
