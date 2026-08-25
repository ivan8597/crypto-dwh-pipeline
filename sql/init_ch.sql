CREATE DATABASE IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS marts.fct_hourly_prices (
    symbol           String,
    hour_ts          DateTime,
    avg_price        Float64,
    min_price        Float64,
    max_price        Float64,
    volatility       Float64,
    price_change_pct Nullable(Float64),
    synced_at        DateTime64(3) DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(synced_at)
ORDER BY (symbol, hour_ts);
