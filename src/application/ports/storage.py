"""
Port: Storage Interface
Defines contract for file storage implementations (S3, local, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path


class IStorage(ABC):
    """Interface for file storage"""
    
    @abstractmethod
    def upload(self, local_path: str, remote_key: str) -> Optional[str]:
        """
        Upload file to storage
        
        Args:
            local_path: Path to local file
            remote_key: Remote storage key/path
            
        Returns:
            URL to access the file, or None if upload failed
        """
        pass
    
    @abstractmethod
    def download(self, remote_key: str, local_path: str) -> bool:
        """
        Download file from storage
        
        Args:
            remote_key: Remote storage key/path
            local_path: Path to save downloaded file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, remote_key: str) -> bool:
        """
        Check if file exists in storage
        
        Args:
            remote_key: Remote storage key/path
            
        Returns:
            True if file exists, False otherwise
        """
        pass
