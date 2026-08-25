import os

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_BUCKET = "raw"

PG_DSN = os.getenv(
    "PG_DSN",
    f"postgresql+psycopg2://{os.getenv('PG_USER', 'dwh')}:"
    f"{os.getenv('PG_PASSWORD', 'dwh')}@{os.getenv('PG_HOST', 'postgres')}:"
    f"{os.getenv('PG_PORT', '5432')}/{os.getenv('PG_DB', 'analytics')}",
)

CH_HOST = os.getenv("CH_HOST", "clickhouse")
API_SYMBOLS = ["BTC-USD", "ETH-USD"]
