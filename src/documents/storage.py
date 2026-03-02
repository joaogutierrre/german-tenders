"""MinIO document storage wrapper."""

import asyncio
import io
import logging

from minio import Minio

from src.config import settings

logger = logging.getLogger(__name__)


class DocumentStorage:
    """S3-compatible document storage using MinIO."""

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
    ) -> None:
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_user
        self.secret_key = secret_key or settings.minio_password
        self.bucket = bucket or settings.minio_bucket
        self._client: Minio | None = None

    def _get_client(self) -> Minio:
        """Get or create the MinIO client."""
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=False,
            )
        return self._client

    async def ensure_bucket(self) -> None:
        """Ensure the storage bucket exists."""
        client = self._get_client()
        exists = await asyncio.to_thread(client.bucket_exists, self.bucket)
        if not exists:
            await asyncio.to_thread(client.make_bucket, self.bucket)
            logger.info("Created bucket: %s", self.bucket)

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload data to MinIO.

        Args:
            key: Object key (path within bucket).
            data: File contents.
            content_type: MIME type.

        Returns:
            The object key.
        """
        client = self._get_client()
        stream = io.BytesIO(data)
        await asyncio.to_thread(
            client.put_object,
            self.bucket,
            key,
            stream,
            length=len(data),
            content_type=content_type,
        )
        logger.info("Uploaded %s (%d bytes)", key, len(data))
        return key

    async def download(self, key: str) -> bytes:
        """Download data from MinIO.

        Args:
            key: Object key.

        Returns:
            File contents as bytes.
        """
        client = self._get_client()
        response = await asyncio.to_thread(client.get_object, self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def exists(self, key: str) -> bool:
        """Check if an object exists in MinIO."""
        client = self._get_client()
        try:
            await asyncio.to_thread(client.stat_object, self.bucket, key)
            return True
        except Exception:
            return False
