import os
import boto3
from dotenv import load_dotenv

def verify_aws_connectivity():
    print("--- AWS Connectivity Diagnostic ---")
    load_dotenv(override=True)
    
    access_key = (os.getenv("AWS_STORAGE_CONNECTION_STRING") or "").strip().strip('"').strip("'")
    secret_key = (os.getenv("AWS_OPEN_AI_KEY") or "").strip().strip('"').strip("'")
    region = os.getenv("REGION", "eu-north-1")
    bucket_name = "orchestra00998"

    print(f"Access Key: {access_key[:4]}...{access_key[-4:] if access_key else 'None'} (Length: {len(access_key)})")
    print(f"Secret Key: [SET] (Length: {len(secret_key)})")
    print(f"Region: {region}")
    print(f"Target Bucket: {bucket_name}")

    if not access_key or not secret_key:
        print("ERROR: Missing credentials in .ENV")
        return

    try:
        session = boto3.Session(
            aws_access_key_id=access_key.strip().strip('"').strip("'"),
            aws_secret_access_key=secret_key.strip().strip('"').strip("'"),
            region_name=region
        )
        
        print("\n0. Checking IAM Identity...")
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"I Identity: {identity.get('Arn')}")
        print(f"I Account: {identity.get('Account')}")

        s3 = session.client("s3")
        
        print("\n1. Testing S3 Connection (list_objects)...")
        # Try a simple operation
        s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
        print("S3 Connectivity Successful!")

        print("\n2. Testing Rekognition Connectivity...")
        rek = session.client("rekognition")
        rek.list_stream_processors(MaxResults=1)
        print("Rekognition Connectivity Successful!")

        print("\n3. Testing Transcribe Connectivity...")
        transcribe = session.client("transcribe")
        transcribe.list_transcription_jobs(MaxResults=1)
        print("Transcribe Connectivity Successful!")

    except Exception as e:
        print(f"\n[ERROR] AWS ERROR: {str(e)}")
        if "SignatureDoesNotMatch" in str(e):
            print("\nPOSSIBLE CAUSES:")
            print("- Secret key is incorrect for this Access Key.")
            print("- Extra spaces/newlines in .ENV file.")
            print("- System clock is out of sync.")
            print("- Credentials do not have permission for this operation.")

if __name__ == "__main__":
    verify_aws_connectivity()
