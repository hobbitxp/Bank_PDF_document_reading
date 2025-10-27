"""
Infrastructure Adapter: S3 Storage
Implements IStorage for AWS S3 with pre-signed URLs
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from application.ports.storage import IStorage


class S3Storage(IStorage):
    """AWS S3 storage adapter with pre-signed URLs"""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        region: str = "ap-southeast-1",
        url_expiration: int = 3600,
        endpoint_url: Optional[str] = None,
        environment: str = "dev"
    ):
        """Initialize S3 client"""
        
        self.bucket_name = bucket_name
        self.region = region
        self.url_expiration = url_expiration
        self.environment = environment  # dev, staging, prod
        
        # Initialize S3 client
        session_kwargs = {"region_name": region}
        
        if aws_access_key and aws_secret_key:
            session_kwargs["aws_access_key_id"] = aws_access_key
            session_kwargs["aws_secret_access_key"] = aws_secret_key
        
        # Add endpoint URL for LocalStack support
        if endpoint_url:
            session_kwargs["endpoint_url"] = endpoint_url
        
        self.s3_client = boto3.client('s3', **session_kwargs)
    
    def upload(
        self,
        file_path: str,
        object_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Upload file to S3 and return pre-signed URL"""
        
        try:
            # Add environment prefix to object key
            object_key_with_env = f"{self.environment}/{object_key}"
            
            # Prepare extra args
            extra_args = {}
            
            if metadata:
                extra_args["Metadata"] = metadata
            
            # Determine content type
            content_type = self._get_content_type(file_path)
            if content_type:
                extra_args["ContentType"] = content_type
            
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key_with_env,
                ExtraArgs=extra_args if extra_args else None
            )
            
            # Generate pre-signed URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key_with_env
                },
                ExpiresIn=self.url_expiration
            )
            
            return url
        
        except ClientError as e:
            raise Exception(f"S3 upload failed: {e}")
    
    def download(
        self,
        object_key: str,
        destination_path: str
    ) -> bool:
        """Download file from S3"""
        
        try:
            # Add environment prefix
            object_key_with_env = f"{self.environment}/{object_key}"
            
            # Create directory if needed
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(
                self.bucket_name,
                object_key_with_env,
                destination_path
            )
            
            return True
        
        except ClientError as e:
            raise Exception(f"S3 download failed: {e}")
    
    def get_presigned_url(
        self,
        object_key: str,
        expiration: Optional[int] = None
    ) -> str:
        """Generate pre-signed URL for existing S3 object"""
        
        try:
            # Add environment prefix
            object_key_with_env = f"{self.environment}/{object_key}"
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key_with_env
                },
                ExpiresIn=expiration or self.url_expiration
            )
            
            return url
        
        except ClientError as e:
            raise Exception(f"Failed to generate pre-signed URL: {e}")
    
    def delete(self, object_key: str) -> bool:
        """Delete object from S3"""
        
        try:
            # Add environment prefix
            object_key_with_env = f"{self.environment}/{object_key}"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key_with_env
            )
            
            return True
        
        except ClientError as e:
            raise Exception(f"S3 delete failed: {e}")
    
    def exists(self, object_key: str) -> bool:
        """Check if object exists in S3"""
        
        try:
            # Add environment prefix
            object_key_with_env = f"{self.environment}/{object_key}"
            
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key_with_env
            )
            return True
        
        except ClientError:
            return False
    
    def _get_content_type(self, file_path: str) -> Optional[str]:
        """Determine content type from file extension"""
        
        ext_map = {
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.txt': 'text/plain'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext)


class LocalStorage(IStorage):
    """Local filesystem storage adapter (fallback when S3 unavailable)"""
    
    def __init__(self, base_path: str = "data/storage"):
        """Initialize local storage"""
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def upload(
        self,
        file_path: str,
        object_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Copy file to local storage"""
        
        import shutil
        
        # Create destination path
        dest_path = self.base_path / object_key
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(file_path, dest_path)
        
        # Save metadata if provided
        if metadata:
            meta_path = dest_path.with_suffix(dest_path.suffix + '.meta.json')
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Return local file path (not a URL)
        return f"file://{dest_path.absolute()}"
    
    def download(
        self,
        object_key: str,
        destination_path: str
    ) -> bool:
        """Copy file from local storage"""
        
        import shutil
        
        source_path = self.base_path / object_key
        
        if not source_path.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        
        # Create destination directory
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Copy file
        shutil.copy2(source_path, destination_path)
        
        return True
    
    def get_presigned_url(
        self,
        object_key: str,
        expiration: Optional[int] = None
    ) -> str:
        """Return local file path (no URL needed)"""
        
        file_path = self.base_path / object_key
        
        if not file_path.exists():
            raise FileNotFoundError(f"Object not found: {object_key}")
        
        return f"file://{file_path.absolute()}"
    
    def delete(self, object_key: str) -> bool:
        """Delete file from local storage"""
        
        file_path = self.base_path / object_key
        
        if file_path.exists():
            file_path.unlink()
            
            # Delete metadata if exists
            meta_path = file_path.with_suffix(file_path.suffix + '.meta.json')
            if meta_path.exists():
                meta_path.unlink()
            
            return True
        
        return False
    
    def exists(self, object_key: str) -> bool:
        """Check if file exists in local storage"""
        
        file_path = self.base_path / object_key
        return file_path.exists()
