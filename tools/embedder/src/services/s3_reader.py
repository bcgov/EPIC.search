import boto3

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
S3 Reader Service module for retrieving files from S3 storage.

This module provides functionality to connect to an S3-compatible storage service
and download files using their object keys. It uses the boto3 library to interact
with the S3 API and retrieves configuration from the application settings.
"""

def read_file_from_s3(object_key):
    """
    Download a file from S3 storage.
    
    Retrieves a file from S3 storage using the provided object key. The S3 connection
    parameters (endpoint, bucket, credentials) are loaded from application settings.
    
    Args:
        object_key (str): The S3 key (path) of the file to download
        
    Returns:
        bytes: The binary content of the downloaded file
        
    Raises:
        boto3.exceptions.Boto3Error: If the S3 request fails (e.g., file not found,
                                     access denied, connection error)
    """
    settings = get_settings()

    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.s3_settings.access_key_id,
        aws_secret_access_key=settings.s3_settings.secret_access_key,
        region_name=settings.s3_settings.region_name,
        endpoint_url=settings.s3_settings.endpoint_uri,
    )
    response = s3.get_object(Bucket=settings.s3_settings.bucket_name, Key=object_key)
    file_data = response["Body"].read()
    return file_data
