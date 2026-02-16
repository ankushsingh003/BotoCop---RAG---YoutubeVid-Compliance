import os
import boto3
from dotenv import load_dotenv

def get_bucket():
    load_dotenv(override=True)
    access_key = (os.getenv("AWS_STORAGE_CONNECTION_STRING") or "").strip().strip('"').strip("'")
    secret_key = (os.getenv("AWS_OPEN_AI_KEY") or "").strip().strip('"').strip("'")
    region = os.getenv("REGION", "eu-central-1")

    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    s3 = session.client("s3")
    buckets = [b['Name'] for b in s3.list_buckets()['Buckets']]
    print("BUCKETS:" + ",".join(buckets))

if __name__ == "__main__":
    get_bucket()
