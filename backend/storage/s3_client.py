"""
S3/MinIO client for object storage
"""
import os
import logging
from typing import Optional, Dict, Any, BinaryIO
import boto3
from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)


class S3Client:
    """
    Client for S3-compatible object storage (AWS S3, MinIO, etc.)
    """
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: str = "us-east-1"
    ):
        """
        Initialize S3 client
        
        Args:
            endpoint_url: S3 endpoint URL (for MinIO or custom S3)
            access_key: AWS access key or MinIO access key
            secret_key: AWS secret key or MinIO secret key
            bucket_name: Default bucket name
            region: AWS region
        """
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("S3_SECRET_KEY")
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "swarm-companies")
        self.region = region
        
        # Initialize boto3 client
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket exists: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket: {self.bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {str(create_error)}")
            else:
                logger.error(f"Error checking bucket: {str(e)}")
    
    def upload_file(
        self,
        file_path: str,
        object_key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a file to S3
        
        Args:
            file_path: Local file path
            object_key: S3 object key (path in bucket)
            bucket: Bucket name (uses default if not specified)
            metadata: Optional metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self.bucket_name
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.client.upload_file(
                file_path,
                bucket,
                object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Uploaded file to s3://{bucket}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload file: {str(e)}")
            return False
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        object_key: str,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a file object to S3
        
        Args:
            file_obj: File-like object
            object_key: S3 object key
            bucket: Bucket name
            metadata: Optional metadata
            
        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self.bucket_name
        
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.client.upload_fileobj(
                file_obj,
                bucket,
                object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Uploaded file object to s3://{bucket}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload file object: {str(e)}")
            return False
    
    def download_file(
        self,
        object_key: str,
        file_path: str,
        bucket: Optional[str] = None
    ) -> bool:
        """
        Download a file from S3
        
        Args:
            object_key: S3 object key
            file_path: Local file path to save to
            bucket: Bucket name
            
        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self.bucket_name
        
        try:
            self.client.download_file(bucket, object_key, file_path)
            logger.info(f"Downloaded s3://{bucket}/{object_key} to {file_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to download file: {str(e)}")
            return False
    
    def delete_file(
        self,
        object_key: str,
        bucket: Optional[str] = None
    ) -> bool:
        """
        Delete a file from S3
        
        Args:
            object_key: S3 object key
            bucket: Bucket name
            
        Returns:
            True if successful, False otherwise
        """
        bucket = bucket or self.bucket_name
        
        try:
            self.client.delete_object(Bucket=bucket, Key=object_key)
            logger.info(f"Deleted s3://{bucket}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False
    
    def file_exists(
        self,
        object_key: str,
        bucket: Optional[str] = None
    ) -> bool:
        """
        Check if a file exists in S3
        
        Args:
            object_key: S3 object key
            bucket: Bucket name
            
        Returns:
            True if exists, False otherwise
        """
        bucket = bucket or self.bucket_name
        
        try:
            self.client.head_object(Bucket=bucket, Key=object_key)
            return True
        except ClientError:
            return False
    
    def generate_presigned_url(
        self,
        object_key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary access
        
        Args:
            object_key: S3 object key
            bucket: Bucket name
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL or None if failed
        """
        bucket = bucket or self.bucket_name
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': object_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for s3://{bucket}/{object_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None
    
    def list_files(
        self,
        prefix: str = "",
        bucket: Optional[str] = None
    ) -> list:
        """
        List files in S3 bucket with optional prefix
        
        Args:
            prefix: Key prefix to filter by
            bucket: Bucket name
            
        Returns:
            List of object keys
        """
        bucket = bucket or self.bucket_name
        
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
            
        except ClientError as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []
    
    def get_file_metadata(
        self,
        object_key: str,
        bucket: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file
        
        Args:
            object_key: S3 object key
            bucket: Bucket name
            
        Returns:
            Metadata dictionary or None if failed
        """
        bucket = bucket or self.bucket_name
        
        try:
            response = self.client.head_object(Bucket=bucket, Key=object_key)
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }
            
        except ClientError as e:
            logger.error(f"Failed to get file metadata: {str(e)}")
            return None
    
    def copy_file(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None
    ) -> bool:
        """
        Copy a file within S3
        
        Args:
            source_key: Source object key
            dest_key: Destination object key
            source_bucket: Source bucket name
            dest_bucket: Destination bucket name
            
        Returns:
            True if successful, False otherwise
        """
        source_bucket = source_bucket or self.bucket_name
        dest_bucket = dest_bucket or self.bucket_name
        
        try:
            copy_source = {'Bucket': source_bucket, 'Key': source_key}
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=dest_bucket,
                Key=dest_key
            )
            
            logger.info(f"Copied s3://{source_bucket}/{source_key} to s3://{dest_bucket}/{dest_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to copy file: {str(e)}")
            return False

# Made with Bob
