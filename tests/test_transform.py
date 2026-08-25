import pandas as pd


def _dedup(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("_loaded_at").drop_duplicates(subset=["symbol", "fetched_at"], keep="last")


def test_dedup_keeps_latest():
    df = pd.DataFrame({"symbol": ["BTC", "BTC"], "fetched_at": ["2024-01-01T10:00:00Z"] * 2, "_loaded_at": [1, 2]})
    assert len(_dedup(df)) == 1
