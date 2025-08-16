"""
S3 Reader Service module for retrieving files from S3 storage.

This module provides functionality to connect to an S3-compatible storage service
and download files using their object keys. It uses the boto3 library to interact
with the S3 API and retrieves configuration from the application settings.
"""

import boto3
from botocore.config import Config
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
    current_app.logger.info(f"S3 Reader: Starting file download for key: {object_key}")
    current_app.logger.info(f"S3 Config - Bucket: {current_app.config.get('S3_BUCKET_NAME')}")
    current_app.logger.info(f"S3 Config - Endpoint: {current_app.config.get('S3_ENDPOINT_URI')}")
    current_app.logger.info(f"S3 Config - Region: {current_app.config.get('S3_REGION')}")
    
    try:
        # Log network diagnostic information first
        current_app.logger.info("S3 Reader: Running network diagnostics...")
        
        # Test basic connectivity
        import socket
        try:
            # Try to resolve DNS
            ip_address = socket.gethostbyname('nrs.objectstore.gov.bc.ca')
            current_app.logger.info(f"S3 Reader: DNS resolution successful - nrs.objectstore.gov.bc.ca -> {ip_address}")
            
            # Try to connect to port 443
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)  # 15 second timeout for diagnostic
            result = sock.connect_ex((ip_address, 443))
            sock.close()
            
            if result == 0:
                current_app.logger.info("S3 Reader: Port 443 connection test SUCCESSFUL")
            else:
                current_app.logger.error(f"S3 Reader: Port 443 connection test FAILED with error code: {result}")
                
        except socket.gaierror as e:
            current_app.logger.error(f"S3 Reader: DNS resolution FAILED: {e}")
        except Exception as e:
            current_app.logger.error(f"S3 Reader: Network diagnostic error: {e}")
        
        # Configure boto3 with more aggressive timeouts and retries for Azure environment
        config = Config(
            connect_timeout=30,      # Increased from 10 to 30 seconds
            read_timeout=300,        # Increased to 5 minutes for large files
            retries={
                'max_attempts': 5,   # Increased retries
                'mode': 'adaptive'   # Use adaptive retry mode
            },
            max_pool_connections=50  # Increase connection pool
        )
        
        s3_client = boto3.client(
             "s3",
            aws_access_key_id=current_app.config["S3_ACCESS_KEY_ID"],
            aws_secret_access_key=current_app.config["S3_SECRET_ACCESS_KEY"],
            region_name=current_app.config["S3_REGION"] if current_app.config["S3_REGION"] else None,
            endpoint_url=current_app.config["S3_ENDPOINT_URI"] if current_app.config["S3_ENDPOINT_URI"] else None,
            config=config
        )
        current_app.logger.info("S3 Reader: S3 client created successfully with enhanced timeout configuration")
        
        current_app.logger.info(f"S3 Reader: Attempting to get object from bucket '{current_app.config['S3_BUCKET_NAME']}' with key '{object_key}'")
        response = s3_client.get_object(Bucket=current_app.config["S3_BUCKET_NAME"], Key=object_key)
        current_app.logger.info("S3 Reader: Successfully retrieved S3 object")
        
        file_data = response["Body"].read()
        current_app.logger.info(f"S3 Reader: Successfully read file data, size: {len(file_data)} bytes")
        return file_data
        
    except Exception as e:
        current_app.logger.error(f"S3 Reader: Error downloading file: {str(e)}")
        current_app.logger.error(f"S3 Reader: Error type: {type(e).__name__}")
        import traceback
        current_app.logger.error(f"S3 Reader: Full traceback: {traceback.format_exc()}")
        raise e
