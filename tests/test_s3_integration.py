"""
S3 Storage Integration Tests with LocalStack
Tests real S3 operations against LocalStack mock service
"""

import pytest
import os
import tempfile
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

from infrastructure.storage.s3_storage import S3Storage

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def localstack_s3_config():
    """Configuration for LocalStack S3 testing"""
    return {
        "bucket_name": "bank-statements-dev",
        "aws_access_key": "test",
        "aws_secret_key": "test",
        "region": "ap-southeast-1",
        "endpoint_url": "http://172.19.0.2:4566"
    }


@pytest.fixture
def s3_storage_localstack(localstack_s3_config):
    """S3Storage adapter configured for LocalStack"""
    
    # Override boto3 to use LocalStack endpoint
    import infrastructure.storage.s3_storage
    original_client = infrastructure.storage.s3_storage.boto3.client
    
    def mock_client(*args, **kwargs):
        kwargs['endpoint_url'] = localstack_s3_config["endpoint_url"]
        return original_client(*args, **kwargs)
    
    # Monkey patch for this test
    infrastructure.storage.s3_storage.boto3.client = mock_client
    
    try:
        storage = S3Storage(
            bucket_name=localstack_s3_config["bucket_name"],
            aws_access_key=localstack_s3_config["aws_access_key"],
            aws_secret_key=localstack_s3_config["aws_secret_key"],
            region=localstack_s3_config["region"]
        )
        
        # Ensure bucket exists
        try:
            storage.s3_client.create_bucket(
                Bucket=localstack_s3_config["bucket_name"],
                CreateBucketConfiguration={'LocationConstraint': localstack_s3_config["region"]}
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'BucketAlreadyOwnedByYou':
                raise
        
        yield storage
        
    finally:
        # Restore original client
        infrastructure.storage.s3_storage.boto3.client = original_client


@pytest.fixture
def test_pdf_file():
    """Create temporary test PDF file"""
    content = """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>
endobj
4 0 obj
<< /Length 55 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test Integration PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
409
%%EOF"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


class TestS3StorageIntegration:
    """Integration tests for S3Storage with LocalStack"""
    
    def test_upload_and_download_pdf(self, s3_storage_localstack, test_pdf_file):
        """Test uploading and downloading PDF file to/from S3"""
        storage = s3_storage_localstack
        object_key = "test-integration/sample.pdf"
        
        # Upload
        presigned_url = storage.upload(
            file_path=test_pdf_file,
            object_key=object_key,
            metadata={"user_id": "test_integration", "file_type": "pdf"}
        )
        
        assert presigned_url is not None
        assert "172.19.0.2:4566" in presigned_url
        assert "bank-statements-dev" in presigned_url
        
        # Verify file exists
        assert storage.exists(object_key) == True
        
        # Download to verify
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_download:
            download_path = temp_download.name
        
        try:
            success = storage.download(object_key, download_path)
            assert success == True
            
            # Verify file content
            with open(test_pdf_file, 'rb') as original:
                with open(download_path, 'rb') as downloaded:
                    assert original.read() == downloaded.read()
        
        finally:
            # Cleanup
            storage.delete(object_key)
            try:
                os.unlink(download_path)
            except FileNotFoundError:
                pass
    
    def test_presigned_url_generation(self, s3_storage_localstack, test_pdf_file):
        """Test pre-signed URL generation"""
        storage = s3_storage_localstack
        object_key = "test-integration/presigned.pdf"
        
        # Upload file first
        storage.upload(test_pdf_file, object_key)
        
        try:
            # Generate pre-signed URL
            url = storage.get_presigned_url(object_key, expiration=300)
            
            assert url is not None
            assert "172.19.0.2:4566" in url
            assert object_key in url
            # LocalStack uses different presigned URL format
            assert ("X-Amz-Expires=300" in url or "Expires=" in url)
        
        finally:
            storage.delete(object_key)
    
    def test_delete_object(self, s3_storage_localstack, test_pdf_file):
        """Test deleting objects from S3"""
        storage = s3_storage_localstack
        object_key = "test-integration/delete-me.pdf"
        
        # Upload file
        storage.upload(test_pdf_file, object_key)
        assert storage.exists(object_key) == True
        
        # Delete file
        success = storage.delete(object_key)
        assert success == True
        
        # Verify deletion
        assert storage.exists(object_key) == False
    
    def test_upload_with_metadata(self, s3_storage_localstack, test_pdf_file):
        """Test uploading with custom metadata"""
        storage = s3_storage_localstack
        object_key = "test-integration/metadata-test.pdf"
        
        metadata = {
            "user_id": "integration_test_user",
            "original_filename": "bank_statement.pdf",
            "upload_timestamp": "2025-10-26T05:30:00Z"
        }
        
        # Upload with metadata
        presigned_url = storage.upload(
            file_path=test_pdf_file,
            object_key=object_key,
            metadata=metadata
        )
        
        assert presigned_url is not None
        
        # Verify object exists
        assert storage.exists(object_key) == True
        
        # Cleanup
        storage.delete(object_key)
    
    def test_upload_failure_handling(self, s3_storage_localstack):
        """Test handling of upload failures"""
        storage = s3_storage_localstack
        
        # Try to upload non-existent file
        with pytest.raises(Exception, match="No such file or directory"):
            storage.upload(
                file_path="/nonexistent/file.pdf",
                object_key="test/failure.pdf"
            )
    
    def test_download_nonexistent_file(self, s3_storage_localstack):
        """Test downloading non-existent file"""
        storage = s3_storage_localstack
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            download_path = temp_file.name
        
        try:
            with pytest.raises(Exception, match="S3 download failed"):
                storage.download("nonexistent/file.pdf", download_path)
        finally:
            try:
                os.unlink(download_path)
            except FileNotFoundError:
                pass


@pytest.mark.integration
def test_localstack_s3_service_running():
    """Test that LocalStack S3 service is accessible"""
    import requests
    
    # Check LocalStack health
    response = requests.get("http://172.19.0.2:4566/_localstack/health")
    assert response.status_code == 200
    
    health_data = response.json()
    assert health_data["services"]["s3"] == "running"


@pytest.mark.integration
def test_boto3_localstack_connection():
    """Test direct boto3 connection to LocalStack"""
    
    client = boto3.client(
        's3',
        endpoint_url='http://172.19.0.2:4566',
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name='ap-southeast-1'
    )
    
    # List buckets (should not raise exception)
    response = client.list_buckets()
    assert "Buckets" in response
    
    # Verify our test bucket exists
    bucket_names = [bucket["Name"] for bucket in response["Buckets"]]
    # Either dev or local bucket should exist
    assert any(name in bucket_names for name in ["bank-statements-dev", "bank-statements-local"])