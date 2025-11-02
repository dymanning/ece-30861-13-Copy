import os
from typing import Optional, BinaryIO
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "my-bucket")


class S3Client:
    def __init__(self):
        # boto3 will resolve credentials from env or role
        self.client = boto3.client("s3", region_name=AWS_REGION)

    def upload_fileobj(self, fileobj: BinaryIO, key: str, extra_args: Optional[dict] = None) -> str:
        self.client.upload_fileobj(fileobj, S3_BUCKET, key, ExtraArgs=extra_args or {})
        return f"s3://{S3_BUCKET}/{key}"

    def download_stream(self, key: str):
        resp = self.client.get_object(Bucket=S3_BUCKET, Key=key)
        return resp["Body"]

    def delete_object(self, key: str):
        self.client.delete_object(Bucket=S3_BUCKET, Key=key)

    def delete_prefix(self, prefix: str):
        paginator = self.client.get_paginator("list_objects_v2")
        delete_keys = []
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                delete_keys.append({"Key": obj["Key"]})
        if not delete_keys:
            return
        for i in range(0, len(delete_keys), 1000):
            chunk = delete_keys[i : i + 1000]
            self.client.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": chunk})

    @staticmethod
    def key_from_uri(uri: str) -> str:
        # expect s3://bucket/key
        if uri.startswith("s3://"):
            # Remove 's3://'
            path = uri[5:]
            # Split into bucket and key
            parts = path.split('/', 1)
            if len(parts) == 2:
                return parts[1]
            # No key present
            return ""
        return uri
