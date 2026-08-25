import boto3
from botocore.client import Config as BotoConfig
from config import S3_ACCESS_KEY, S3_ENDPOINT, S3_SECRET_KEY


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
    )
