"""S3 / MinIO object storage abstraction.

Images never transit the API: clients PUT directly to presigned URLs, and workers GET
directly. The control plane only mints URLs and stores keys.
"""
from __future__ import annotations

import uuid

import boto3
from botocore.client import Config

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

log = get_logger(__name__)


class StorageService:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            use_ssl=settings.s3_use_ssl,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.s3_bucket

    def ensure_bucket(self) -> None:
        existing = {b["Name"] for b in self._client.list_buckets().get("Buckets", [])}
        if self._bucket not in existing:
            self._client.create_bucket(Bucket=self._bucket)
            log.info("created bucket", bucket=self._bucket)

    @staticmethod
    def build_key(dataset_id: uuid.UUID, filename: str) -> str:
        # prefix-shard by a uuid segment to avoid S3 hot partitions at scale
        shard = uuid.uuid4().hex[:2]
        return f"datasets/{dataset_id}/{shard}/{uuid.uuid4().hex}_{filename}"

    def presign_put(self, key: str, expires: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )

    def presign_get(self, key: str, expires: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get_bytes(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()


storage = StorageService()
