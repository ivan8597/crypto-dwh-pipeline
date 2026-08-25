import json
from datetime import datetime, timezone

import pandas as pd
from config import PG_DSN, S3_BUCKET
from s3_client import get_s3_client
from sqlalchemy import create_engine, text

DDL = """
CREATE SCHEMA IF NOT EXISTS staging;
CREATE TABLE IF NOT EXISTS staging.crypto_prices_raw (
    symbol text, price numeric, volume_24h numeric, fetched_at timestamptz,
    _loaded_at timestamptz DEFAULT now()
);
"""


def list_keys(s3, prefix: str) -> list[str]:
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        keys.extend(obj["Key"] for obj in page.get("Contents", []))
    return keys


def read_rows(s3, keys: list[str]) -> list[dict]:
    rows = []
    for key in keys:
        body = s3.get_object(Bucket=S3_BUCKET, Key=key)["Body"]
        rows.append(json.loads(body.read()))
    return rows


def load_keys(keys: list[str]) -> int:
    """Load exactly the objects produced by extract, without rescanning the day."""
    if not keys:
        return 0
    s3 = get_s3_client()
    df = pd.DataFrame(read_rows(s3, keys))
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(DDL))
    df.to_sql("crypto_prices_raw", engine, schema="staging", if_exists="append", index=False)
    return len(df)


def load_batch(dt: str) -> int:
    s3 = get_s3_client()
    return load_keys(list_keys(s3, f"crypto/dt={dt}/"))


if __name__ == "__main__":
    load_batch(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
