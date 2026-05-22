"""
File manager for high-level file operations
"""
import os
import logging
from typing import Optional, Dict, Any
from .s3_client import S3Client


logger = logging.getLogger(__name__)


class FileManager:
    """
    High-level file management service
    
    Provides abstraction over S3 storage for company files
    """
    
    def __init__(self, s3_client: Optional[S3Client] = None):
        """
        Initialize file manager
        
        Args:
            s3_client: S3 client instance (creates default if not provided)
        """
        self.s3 = s3_client or S3Client()
    
    def store_company(
        self,
        company_id: str,
        archive_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Store a company archive in S3
        
        Args:
            company_id: Company ID
            archive_path: Local path to archive file
            metadata: Optional metadata
            
        Returns:
            S3 object key or None if failed
        """
        object_key = f"companies/{company_id}/source.zip"
        
        # Prepare metadata
        s3_metadata = {}
        if metadata:
            # Convert metadata to strings (S3 requirement)
            s3_metadata = {
                k: str(v) for k, v in metadata.items()
                if isinstance(v, (str, int, float, bool))
            }
        
        # Upload to S3
        success = self.s3.upload_file(
            archive_path,
            object_key,
            metadata=s3_metadata
        )
        
        if success:
            logger.info(f"Stored company {company_id} in S3")
            return object_key
        
        return None
    
    def retrieve_company(
        self,
        company_id: str,
        download_path: str
    ) -> bool:
        """
        Retrieve a company archive from S3
        
        Args:
            company_id: Company ID
            download_path: Local path to save archive
            
        Returns:
            True if successful, False otherwise
        """
        object_key = f"companies/{company_id}/source.zip"
        
        # Ensure download directory exists
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        
        # Download from S3
        success = self.s3.download_file(object_key, download_path)
        
        if success:
            logger.info(f"Retrieved company {company_id} from S3")
        
        return success
    
    def delete_company(self, company_id: str) -> bool:
        """
        Delete a company archive from S3
        
        Args:
            company_id: Company ID
            
        Returns:
            True if successful, False otherwise
        """
        object_key = f"companies/{company_id}/source.zip"
        
        success = self.s3.delete_file(object_key)
        
        if success:
            logger.info(f"Deleted company {company_id} from S3")
        
        return success
    
    def company_exists(self, company_id: str) -> bool:
        """
        Check if a company archive exists in S3
        
        Args:
            company_id: Company ID
            
        Returns:
            True if exists, False otherwise
        """
        object_key = f"companies/{company_id}/source.zip"
        return self.s3.file_exists(object_key)
    
    def get_company_download_url(
        self,
        company_id: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate a presigned download URL for a company
        
        Args:
            company_id: Company ID
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or None if failed
        """
        object_key = f"companies/{company_id}/source.zip"
        
        url = self.s3.generate_presigned_url(object_key, expiration=expiration)
        
        if url:
            logger.info(f"Generated download URL for company {company_id}")
        
        return url
    
    def get_company_metadata(self, company_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a company archive
        
        Args:
            company_id: Company ID
            
        Returns:
            Metadata dictionary or None if not found
        """
        object_key = f"companies/{company_id}/source.zip"
        return self.s3.get_file_metadata(object_key)
    
    def list_companies(self, user_id: Optional[str] = None) -> list:
        """
        List all company archives
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of company IDs
        """
        prefix = "companies/"
        if user_id:
            prefix = f"companies/{user_id}/"
        
        files = self.s3.list_files(prefix)
        
        # Extract company IDs from file paths
        company_ids = []
        for file_path in files:
            parts = file_path.split('/')
            if len(parts) >= 2:
                company_id = parts[1]
                if company_id not in company_ids:
                    company_ids.append(company_id)
        
        return company_ids
    
    def cleanup_old_files(self, days: int = 30) -> int:
        """
        Clean up old company archives
        
        Args:
            days: Delete files older than this many days
            
        Returns:
            Number of files deleted
        """
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = 0
        
        # List all company files
        files = self.s3.list_files("companies/")
        
        for file_path in files:
            # Get file metadata
            metadata = self.s3.get_file_metadata(file_path)
            
            if metadata:
                last_modified = metadata.get('last_modified')
                
                # Check if file is old enough
                if last_modified and last_modified < cutoff_date:
                    if self.s3.delete_file(file_path):
                        deleted_count += 1
                        logger.info(f"Deleted old file: {file_path}")
        
        logger.info(f"Cleaned up {deleted_count} old files")
        return deleted_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage stats
        """
        files = self.s3.list_files("companies/")
        
        total_size = 0
        file_count = len(files)
        
        for file_path in files:
            metadata = self.s3.get_file_metadata(file_path)
            if metadata:
                total_size += metadata.get('size', 0)
        
        return {
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2)
        }
    
    def backup_company(
        self,
        company_id: str,
        backup_bucket: Optional[str] = None
    ) -> bool:
        """
        Create a backup of a company archive
        
        Args:
            company_id: Company ID
            backup_bucket: Optional backup bucket name
            
        Returns:
            True if successful, False otherwise
        """
        source_key = f"companies/{company_id}/source.zip"
        dest_key = f"backups/companies/{company_id}/source.zip"
        
        success = self.s3.copy_file(
            source_key,
            dest_key,
            dest_bucket=backup_bucket
        )
        
        if success:
            logger.info(f"Backed up company {company_id}")
        
        return success

# Made with Bob
