import os
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseStorageService(ABC):
    """Abstract storage interface for persistent Earth system datasets."""

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read binary data from path."""
        pass

    @abstractmethod
    def write(self, path: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Write binary data to path and return URI/identifier."""
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if path exists."""
        pass

    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete path. Returns True if deleted or did not exist."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """List file paths matching prefix."""
        pass

    @abstractmethod
    def get_metadata(self, path: str) -> Dict[str, Any]:
        """Get file metadata (size, updated_at, content_type)."""
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a local file to storage."""
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a storage object to local filesystem."""
        pass


class LocalStorageService(BaseStorageService):
    """
    Local filesystem storage provider for offline and local development.
    Requires ZERO GCP credentials and operates within workspace data directory.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if not base_dir:
            base_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "data", "storage")
            )
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        logger.info(f"LocalStorageService initialized at {self.base_dir}")

    def _full_path(self, path: str) -> str:
        clean = path.replace("\\", "/").lstrip("/")
        return os.path.join(self.base_dir, clean)

    def read(self, path: str) -> bytes:
        full = self._full_path(path)
        if not os.path.exists(full):
            raise FileNotFoundError(f"Storage object not found: {path}")
        with open(full, "rb") as f:
            return f.read()

    def write(self, path: str, data: bytes, content_type: Optional[str] = None) -> str:
        full = self._full_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as f:
            f.write(data)
        return full

    def exists(self, path: str) -> bool:
        return os.path.exists(self._full_path(path))

    def delete(self, path: str) -> bool:
        full = self._full_path(path)
        if os.path.exists(full):
            os.remove(full)
            return True
        return False

    def list_files(self, prefix: str = "") -> List[str]:
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        results = []
        for root, _, files in os.walk(self.base_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.base_dir).replace("\\", "/")
                if not clean_prefix or rel_path.startswith(clean_prefix):
                    results.append(rel_path)
        return sorted(results)

    def get_metadata(self, path: str) -> Dict[str, Any]:
        full = self._full_path(path)
        if not os.path.exists(full):
            raise FileNotFoundError(f"Storage object not found: {path}")
        stat = os.stat(full)
        return {
            "path": path,
            "size_bytes": stat.st_size,
            "updated_at": stat.st_mtime,
            "backend": "local",
        }

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        full = self._full_path(remote_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(local_path, "rb") as src, open(full, "wb") as dst:
            dst.write(src.read())
        return True

    def download_file(self, remote_path: str, local_path: str) -> bool:
        full = self._full_path(remote_path)
        if not os.path.exists(full):
            return False
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        with open(full, "rb") as src, open(local_path, "wb") as dst:
            dst.write(src.read())
        return True


class GCSStorageService(BaseStorageService):
    """
    Google Cloud Storage provider for production deployment.
    Uses Google Application Default Credentials (ADC) - no committed service account keys.
    """

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        self.bucket_name = bucket_name
        self.project_id = project_id

        try:
            from google.cloud import storage
            self._client = storage.Client(project=self.project_id) if self.project_id else storage.Client()
            self._bucket = self._client.bucket(self.bucket_name)
            logger.info(f"GCSStorageService initialized for bucket 'gs://{self.bucket_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Storage client: {e}")
            raise

    def read(self, path: str) -> bytes:
        clean = path.replace("\\", "/").lstrip("/")
        blob = self._bucket.blob(clean)
        if not blob.exists():
            raise FileNotFoundError(f"GCS object not found: gs://{self.bucket_name}/{clean}")
        return blob.download_as_bytes()

    def write(self, path: str, data: bytes, content_type: Optional[str] = None) -> str:
        clean = path.replace("\\", "/").lstrip("/")
        blob = self._bucket.blob(clean)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{self.bucket_name}/{clean}"

    def exists(self, path: str) -> bool:
        clean = path.replace("\\", "/").lstrip("/")
        blob = self._bucket.blob(clean)
        return blob.exists()

    def delete(self, path: str) -> bool:
        clean = path.replace("\\", "/").lstrip("/")
        blob = self._bucket.blob(clean)
        if blob.exists():
            blob.delete()
            return True
        return False

    def list_files(self, prefix: str = "") -> List[str]:
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        blobs = self._client.list_blobs(self._bucket, prefix=clean_prefix)
        return [b.name for b in blobs]

    def get_metadata(self, path: str) -> Dict[str, Any]:
        clean = path.replace("\\", "/").lstrip("/")
        blob = self._bucket.get_blob(clean)
        if not blob:
            raise FileNotFoundError(f"GCS object not found: gs://{self.bucket_name}/{clean}")
        return {
            "path": clean,
            "size_bytes": blob.size,
            "updated_at": blob.updated.isoformat() if blob.updated else None,
            "content_type": blob.content_type,
            "backend": "gcs",
            "bucket": self.bucket_name,
        }

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        clean = remote_path.replace("\\", "/").lstrip("/")
        blob = self._bucket.blob(clean)
        blob.upload_from_filename(local_path)
        return True

    def download_file(self, remote_path: str, local_path: str) -> bool:
        clean = remote_path.replace("\\", "/").lstrip("/")
        blob = self._bucket.blob(clean)
        if not blob.exists():
            return False
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        blob.download_to_filename(local_path)
        return True


class VercelBlobStorageService(BaseStorageService):
    """
    Vercel Blob storage provider for production serverless deployment.
    Communicates with Vercel Blob REST API using standard HTTP (requests).
    Zero heavy cloud SDK dependencies.
    """

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("BLOB_READ_WRITE_TOKEN", "")
        if not self.token:
            raise ValueError("BLOB_READ_WRITE_TOKEN is required for VercelBlobStorageService")
        self.base_url = "https://blob.vercel-storage.com"
        logger.info("VercelBlobStorageService initialized with configured token.")

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}"}
        if extra:
            h.update(extra)
        return h

    def _get_blob_info(self, path: str) -> Optional[Dict[str, Any]]:
        import requests
        clean = path.replace("\\", "/").lstrip("/")
        try:
            resp = requests.get(
                self.base_url,
                params={"prefix": clean},
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                for b in resp.json().get("blobs", []):
                    if b.get("pathname") == clean:
                        return b
        except Exception as e:
            logger.warning(f"Error checking Vercel Blob existence for {clean}: {e}")
        return None

    def read(self, path: str) -> bytes:
        import requests
        info = self._get_blob_info(path)
        if not info or not info.get("url"):
            raise FileNotFoundError(f"Vercel Blob not found: {path}")
        resp = requests.get(info["url"], timeout=30)
        resp.raise_for_status()
        return resp.content

    def write(self, path: str, data: bytes, content_type: Optional[str] = None) -> str:
        import requests
        clean = path.replace("\\", "/").lstrip("/")
        headers = self._headers({"x-add-random-suffix": "false"})
        if content_type:
            headers["content-type"] = content_type

        resp = requests.put(
            f"{self.base_url}/{clean}",
            data=data,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("url", f"vercel-blob://{clean}")

    def exists(self, path: str) -> bool:
        return self._get_blob_info(path) is not None

    def delete(self, path: str) -> bool:
        import requests
        info = self._get_blob_info(path)
        if not info or not info.get("url"):
            return False
        try:
            resp = requests.post(
                f"{self.base_url}/delete",
                json={"urls": [info["url"]]},
                headers=self._headers(),
                timeout=15,
            )
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Error deleting Vercel Blob {path}: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        import requests
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        params = {"prefix": clean_prefix} if clean_prefix else {}
        try:
            resp = requests.get(
                self.base_url,
                params=params,
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code == 200:
                return [b.get("pathname", "") for b in resp.json().get("blobs", [])]
        except Exception as e:
            logger.warning(f"Error listing Vercel Blobs: {e}")
        return []

    def get_metadata(self, path: str) -> Dict[str, Any]:
        info = self._get_blob_info(path)
        if not info:
            raise FileNotFoundError(f"Vercel Blob not found: {path}")
        return {
            "path": info.get("pathname", path),
            "size_bytes": info.get("size", 0),
            "updated_at": info.get("uploadedAt"),
            "content_type": info.get("contentType"),
            "backend": "vercel_blob",
            "url": info.get("url"),
        }

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        with open(local_path, "rb") as f:
            data = f.read()
        self.write(remote_path, data)
        return True

    def download_file(self, remote_path: str, local_path: str) -> bool:
        try:
            content = self.read(remote_path)
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.warning(f"Failed to download {remote_path} from Vercel Blob: {e}")
            return False


class S3StorageService(BaseStorageService):
    """
    S3-compatible object storage provider (AWS S3, Cloudflare R2, MinIO, Supabase).
    Configurable via standard AWS credentials and optional endpoint URL.
    """

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name

        try:
            import boto3
            self._s3 = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region_name,
            )
            logger.info(f"S3StorageService initialized for bucket '{self.bucket_name}'")
        except ImportError:
            raise ImportError("boto3 is required for S3StorageService. Install via pip install boto3.")

    def read(self, path: str) -> bytes:
        clean = path.replace("\\", "/").lstrip("/")
        resp = self._s3.get_object(Bucket=self.bucket_name, Key=clean)
        return resp["Body"].read()

    def write(self, path: str, data: bytes, content_type: Optional[str] = None) -> str:
        clean = path.replace("\\", "/").lstrip("/")
        extra_args = {"ContentType": content_type} if content_type else {}
        self._s3.put_object(Bucket=self.bucket_name, Key=clean, Body=data, **extra_args)
        return f"s3://{self.bucket_name}/{clean}"

    def exists(self, path: str) -> bool:
        import botocore.exceptions
        clean = path.replace("\\", "/").lstrip("/")
        try:
            self._s3.head_object(Bucket=self.bucket_name, Key=clean)
            return True
        except botocore.exceptions.ClientError:
            return False

    def delete(self, path: str) -> bool:
        clean = path.replace("\\", "/").lstrip("/")
        self._s3.delete_object(Bucket=self.bucket_name, Key=clean)
        return True

    def list_files(self, prefix: str = "") -> List[str]:
        clean_prefix = prefix.replace("\\", "/").lstrip("/")
        resp = self._s3.list_objects_v2(Bucket=self.bucket_name, Prefix=clean_prefix)
        return [item["Key"] for item in resp.get("Contents", [])]

    def get_metadata(self, path: str) -> Dict[str, Any]:
        clean = path.replace("\\", "/").lstrip("/")
        resp = self._s3.head_object(Bucket=self.bucket_name, Key=clean)
        return {
            "path": clean,
            "size_bytes": resp["ContentLength"],
            "updated_at": resp["LastModified"].isoformat(),
            "content_type": resp.get("ContentType"),
            "backend": "s3",
            "bucket": self.bucket_name,
        }

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        clean = remote_path.replace("\\", "/").lstrip("/")
        self._s3.upload_file(local_path, self.bucket_name, clean)
        return True

    def download_file(self, remote_path: str, local_path: str) -> bool:
        clean = remote_path.replace("\\", "/").lstrip("/")
        os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
        self._s3.download_file(self.bucket_name, clean, local_path)
        return True


_storage_instance: Optional[BaseStorageService] = None


def get_storage_service() -> BaseStorageService:
    """
    Factory to retrieve storage service based on environment configuration.
    Priority:
    1. Vercel Blob (if STORAGE_BACKEND=vercel_blob or BLOB_READ_WRITE_TOKEN is set)
    2. S3 / R2 (if STORAGE_BACKEND=s3 and S3_BUCKET is set)
    3. GCS (if STORAGE_BACKEND=gcs and BHIMA_GCS_BUCKET is set)
    4. LocalStorageService (default fallback for zero-credential offline/local development)
    """
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    from app.config import get_settings
    settings = get_settings()

    backend_type = os.environ.get("STORAGE_BACKEND", settings.storage_backend).lower()
    vercel_token = os.environ.get("BLOB_READ_WRITE_TOKEN", settings.blob_read_write_token)

    # 1. Vercel Blob
    if backend_type == "vercel_blob" or vercel_token:
        try:
            _storage_instance = VercelBlobStorageService(token=vercel_token)
            return _storage_instance
        except Exception as e:
            logger.warning(
                f"Falling back from VercelBlobStorageService because initialization failed: {e}"
            )

    # 2. S3 / R2
    s3_bucket = os.environ.get("S3_BUCKET", settings.s3_bucket)
    if backend_type == "s3" and s3_bucket:
        try:
            _storage_instance = S3StorageService(
                bucket_name=s3_bucket,
                endpoint_url=os.environ.get("S3_ENDPOINT_URL", settings.s3_endpoint_url) or None,
                region_name=os.environ.get("AWS_REGION", settings.aws_region),
            )
            return _storage_instance
        except Exception as e:
            logger.warning(f"Falling back from S3StorageService: {e}")

    # 3. GCS (legacy fallback)
    bucket_name = os.environ.get("BHIMA_GCS_BUCKET", settings.bhima_gcs_bucket)
    if backend_type == "gcs" and bucket_name:
        try:
            _storage_instance = GCSStorageService(
                bucket_name=bucket_name,
                project_id=os.environ.get("GCP_PROJECT_ID", settings.gcp_project_id) or None,
            )
            return _storage_instance
        except Exception as e:
            logger.warning(
                f"Falling back to LocalStorageService because GCS initialization failed: {e}"
            )

    # 4. Local storage fallback
    _storage_instance = LocalStorageService()
    return _storage_instance
