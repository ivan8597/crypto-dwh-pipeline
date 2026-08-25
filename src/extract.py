import json
from datetime import datetime, timezone

import requests
from botocore.exceptions import ClientError
from config import API_SYMBOLS, S3_BUCKET
from s3_client import get_s3_client
from tenacity import retry, stop_after_attempt, wait_exponential


def ensure_bucket(s3):
    try:
        s3.head_bucket(Bucket=S3_BUCKET)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=S3_BUCKET)
        else:
            raise


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=30))
def fetch_ticker(symbol: str) -> dict:
    response = requests.get(
        f"https://api.exchange.coinbase.com/products/{symbol}/ticker", timeout=30
    )
    response.raise_for_status()
    return response.json()


def run() -> list[str]:
    """API -> S3. Returns the exact keys for downstream XCom loading."""
    s3 = get_s3_client()
    ensure_bucket(s3)
    now = datetime.now(timezone.utc)
    keys = []
    for symbol in API_SYMBOLS:
        data = fetch_ticker(symbol)
        payload = {
            "symbol": symbol,
            "price": float(data["price"]),
            "volume_24h": float(data["volume"]),
            "fetched_at": now.isoformat(),
        }
        key = f"crypto/dt={now:%Y-%m-%d}/{int(now.timestamp())}_{symbol}.json"
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=json.dumps(payload))
        keys.append(key)
        print(f"s3://{S3_BUCKET}/{key}")
    return keys


if __name__ == "__main__":
    run()
