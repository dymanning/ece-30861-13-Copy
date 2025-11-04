import os
from typing import Optional, BinaryIO
import boto3
from pathlib import Path

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "my-bucket")
S3_LOCAL_DIR = os.getenv("S3_LOCAL_DIR")


class S3Client:
    def __init__(self):
        self.local_dir = Path(S3_LOCAL_DIR) if S3_LOCAL_DIR else None
        if self.local_dir:
            self.local_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.client = boto3.client("s3", region_name=AWS_REGION)

    def _local_path(self, key: str) -> Path:
        assert self.local_dir is not None
        bucket_dir = self.local_dir / S3_BUCKET
        bucket_dir.mkdir(parents=True, exist_ok=True)
        return bucket_dir / key

    def upload_fileobj(self, fileobj: BinaryIO, key: str, extra_args: Optional[dict] = None) -> str:
        if self.local_dir:
            p = self._local_path(key)
            p.parent.mkdir(parents=True, exist_ok=True)
            data = fileobj.read()
            if isinstance(data, str):
                data = data.encode()
            with p.open("wb") as f:
                f.write(data)
            return f"file://{p}"

        self.client.upload_fileobj(fileobj, S3_BUCKET, key, ExtraArgs=extra_args or {})
        return f"s3://{S3_BUCKET}/{key}"

    def download_stream(self, key: str):
        if self.local_dir:
            p = self._local_path(key)
            if not p.exists():
                raise FileNotFoundError(key)
            return p.open("rb")

        resp = self.client.get_object(Bucket=S3_BUCKET, Key=key)
        return resp["Body"]

    def delete_object(self, key: str):
        if self.local_dir:
            p = self._local_path(key)
            try:
                p.unlink()
            except FileNotFoundError:
                pass
            return

        self.client.delete_object(Bucket=S3_BUCKET, Key=key)

    def delete_prefix(self, prefix: str):
        if self.local_dir:
            base = self.local_dir / S3_BUCKET
            for p in base.rglob("*"):
                rel = p.relative_to(base)
                if str(rel).startswith(prefix):
                    try:
                        p.unlink()
                    except Exception:
                        pass
            return

        paginator = self.client.get_paginator("list_objects_v2")
        delete_keys = []
        for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                delete_keys.append({"Key": obj["Key"]})
        if not delete_keys:
            return
        for i in range(0, len(delete_keys), 1000):
            chunk = delete_keys[i: i + 1000]
            self.client.delete_objects(Bucket=S3_BUCKET, Delete={"Objects": chunk})

    @staticmethod
    def key_from_uri(uri: str) -> str:
        if uri.startswith("s3://"):
            parts = uri.split("/", 3)
            if len(parts) >= 4:
                return parts[3]
            if len(parts) == 3:
                return parts[2]
        if uri.startswith("file://"):
            return uri[len("file://"):]
        return uri
