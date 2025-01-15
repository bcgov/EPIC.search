import boto3
import io
import os
def read_file_from_s3(object_key):

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-west-2"),
        endpoint_url=os.environ.get("AWS_ENDPOINT_URI"),
    )
    response = s3.get_object(Bucket=os.environ.get("AWS_BUCKET_NAME"), Key=object_key)
    pdf_data = response['Body'].read()
    return pdf_data