import boto3

from whoami_back.utils.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# Initialize shared object
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


def get_s3_object_uri(bucket: str, object_key: str):
    return f"https://{bucket}.s3.amazonaws.com/{object_key}"
