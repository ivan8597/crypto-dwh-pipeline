import pandas as pd
from clickhouse_driver import Client
from config import CH_HOST, PG_DSN
from sqlalchemy import create_engine, text


def sync() -> int:
    """Sync a rolling 48-hour window using versioned ReplacingMergeTree inserts."""
    pg = create_engine(PG_DSN)
    df = pd.read_sql(
        text("""SELECT * FROM analytics_marts.fct_hourly_prices
                 WHERE hour_ts >= now() - interval '48 hours'"""), pg
    )
    if df.empty:
        return 0
    client = Client(host=CH_HOST)
    df["price_change_pct"] = df["price_change_pct"].where(df["price_change_pct"].notna(), None)
    columns = [
        "symbol", "hour_ts", "avg_price", "min_price", "max_price",
        "volatility", "price_change_pct",
    ]
    rows = list(df[columns].itertuples(index=False, name=None))
    client.execute(
        "INSERT INTO marts.fct_hourly_prices "
        "(symbol, hour_ts, avg_price, min_price, max_price, volatility, price_change_pct) "
        "VALUES",
        rows,
    )
    return len(df)


if __name__ == "__main__":
    sync()
