"""
S3 Reader Service module for retrieving files from S3 storage.

This module provides functionality to connect to an S3-compatible storage service
and download files using their object keys. It uses the boto3 library to interact
with the S3 API and retrieves configuration from the application settings.
"""

import boto3
from flask import current_app

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
    s3_client = boto3.client(
         "s3",
        aws_access_key_id=current_app.config["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=current_app.config["S3_SECRET_ACCESS_KEY"],
        region_name=current_app.config["S3_REGION"] if current_app.config["S3_REGION"] else None,
        endpoint_url=current_app.config["S3_ENDPOINT_URI"] if current_app.config["S3_ENDPOINT_URI"] else None
    )
    response = s3_client.get_object(Bucket=current_app.config["S3_BUCKET_NAME"], Key=object_key)
    file_data = response["Body"].read()
    return file_data
