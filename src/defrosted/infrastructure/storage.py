"""
S3 client for lease documents and listing photos.

We validate MIME type and size before any upload (security checklist §13).
boto3's client is thread-safe and cheap to reuse, so we create one per process.
"""
from __future__ import annotations

import boto3
from botocore.client import BaseClient

from ..config import Settings

# Documents are PDFs; photos are common web image formats.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB

_client: BaseClient | None = None


def get_s3_client(settings: Settings) -> BaseClient:
    """Return the process-wide S3 client, creating it on first use."""
    global _client
    if _client is None:
        _client = boto3.client("s3", region_name=settings.aws_region)
    return _client


def upload_document(
    settings: Settings, key: str, body: bytes, content_type: str
) -> str:
    """
    Upload bytes to S3 after validating type and size. Returns the object key.
    Fails loudly on invalid input rather than silently storing junk.
    """
    if content_type not in ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Refusing to upload content_type '{content_type}'. "
            f"Allowed types: {sorted(ALLOWED_MIME_TYPES)}."
        )
    if len(body) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Upload is {len(body)} bytes, which exceeds the {MAX_UPLOAD_BYTES}-byte limit."
        )
    client = get_s3_client(settings)
    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    return key
