# backend/app/s3_client.py
import boto3
import os

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")

session = boto3.session.Session(
    region_name=AWS_REGION,
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

s3 = session.client("s3")

def upload_fileobj(fileobj, key: str, content_type: str):
    s3.upload_fileobj(
        Fileobj=fileobj,
        Bucket=AWS_S3_BUCKET,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )

def delete_object(key: str):
    s3.delete_object(Bucket=AWS_S3_BUCKET, Key=key)

def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": AWS_S3_BUCKET, "Key": key},
        ExpiresIn=expires_in,
    )