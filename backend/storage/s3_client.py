"""
Sovereign-friendly storage client.
Supports real S3/MinIO if boto3 is present, otherwise falls back to local storage
to maintain the 100% FOSS / zero-cost mandate.
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None
    ClientError = Exception

logger = logging.getLogger(__name__)


class S3Client:
    """
    Client for S3-compatible object storage (AWS S3, MinIO, etc.) or local FOSS fallback.
    """
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: str = "us-east-1"
    ):
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY")
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "swarm-companies")
        self.region = region
        
        self.local_mode = boto3 is None or os.getenv("STORAGE_MODE") == "local"
        
        if self.local_mode:
            self.base_path = Path(os.getenv("LOCAL_STORAGE_DIR", "./output/storage"))
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"S3Client initialized in LOCAL mode at {self.base_path}")
        else:
            try:
                self.client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region
                )
                self._ensure_bucket_exists()
                logger.info(f"S3Client initialized in S3 mode for bucket {self.bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to init S3 client, falling back to local: {e}")
                self.local_mode = True
                self.base_path = Path("./output/storage")
                self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _ensure_bucket_exists(self):
        if self.local_mode:
            return
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            # Simple fallback for missing bucket
            try:
                self.client.create_bucket(Bucket=self.bucket_name)
            except Exception:
                pass
    
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        if self.local_mode:
            import shutil
            dest = self.base_path / object_key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest)
            return True
        
        try:
            self.client.upload_file(file_path, bucket or self.bucket_name, object_key)
            return True
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def download_file(
        self,
        object_key: str,
        file_path: str,
        bucket: Optional[str] = None
    ) -> bool:
        if self.local_mode:
            import shutil
            src = self.base_path / object_key
            if not src.exists():
                return False
            shutil.copy2(src, file_path)
            return True
        
        try:
            self.client.download_file(bucket or self.bucket_name, object_key, file_path)
            return True
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False

    def delete_file(self, object_key: str, bucket: Optional[str] = None) -> bool:
        if self.local_mode:
            path = self.base_path / object_key
            if path.exists():
                path.unlink()
            return True
        try:
            self.client.delete_object(Bucket=bucket or self.bucket_name, Key=object_key)
            return True
        except Exception:
            return False

    def file_exists(self, object_key: str, bucket: Optional[str] = None) -> bool:
        if self.local_mode:
            return (self.base_path / object_key).exists()
        try:
            self.client.head_object(Bucket=bucket or self.bucket_name, Key=object_key)
            return True
        except Exception:
            return False
