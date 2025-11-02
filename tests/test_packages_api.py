import os
import io
import sys
import importlib

from fastapi.testclient import TestClient


class FakeS3:
    def __init__(self):
        self.store = {}

    def upload_fileobj(self, fileobj, Bucket, Key, ExtraArgs=None):
        # read all bytes from file-like
        data = fileobj.read()
        # ensure bytes
        if isinstance(data, str):
            data = data.encode()
        self.store[Key] = data

    def get_object(self, Bucket, Key):
        if Key not in self.store:
            raise Exception("NoSuchKey")
        return {"Body": io.BytesIO(self.store[Key])}

    def delete_object(self, Bucket, Key):
        self.store.pop(Key, None)

    def get_paginator(self, name):
        class Paginator:
            def __init__(self, store):
                self.store = store

            def paginate(self, Bucket, Prefix):
                contents = [
                    {"Key": k} for k in self.store.keys() if k.startswith(Prefix)
                ]
                if contents:
                    yield {"Contents": contents}
                else:
                    yield {}

        return Paginator(self.store)


def setup_module(module):
    # Ensure repo root is on sys.path so we can import phase2.src packages
    root = os.getcwd()
    if root not in sys.path:
        sys.path.insert(0, root)

    # Use in-memory SQLite for tests
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("S3_BUCKET_NAME", "test-bucket")

    # Monkeypatch boto3.client before importing the app so the S3Client picks up fake
    import boto3

    module._fake_s3 = FakeS3()

    def fake_client(*args, **kwargs):
        return module._fake_s3

    boto3.client = fake_client

    # Import the FastAPI app after env vars and boto3 patch
    global app, client
    pkg_main = importlib.import_module("phase2.src.packages_api.main")
    app = pkg_main.app
    client = TestClient(app)


def test_upload_get_and_delete_cycle():
    # Upload a package
    file_bytes = b"dummy-zip-content"
    files = {"file": ("model.zip", file_bytes, "application/zip")}
    data = {"name": "test-model", "version": "0.1", "metadata": '{"k": "v"}'}

    resp = client.post("/packages", data=data, files=files)
    assert resp.status_code == 201, resp.text
    j = resp.json()
    assert j["name"] == "test-model"
    pkg_id = j["id"]
    assert j.get("s3_uri") and j["s3_uri"].startswith("s3://")

    # Download full package
    resp2 = client.get(f"/packages/{pkg_id}")
    assert resp2.status_code == 200
    assert resp2.content == file_bytes

    # Delete package
    resp3 = client.delete(f"/packages/{pkg_id}")
    assert resp3.status_code == 204

    # Confirm deleted
    resp4 = client.get(f"/packages/{pkg_id}")
    assert resp4.status_code == 404
