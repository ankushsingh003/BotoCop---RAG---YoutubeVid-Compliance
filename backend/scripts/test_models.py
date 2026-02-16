import os
import boto3
from dotenv import load_dotenv

def test_models():
    load_dotenv(override=True)
    access_key = (os.getenv("AWS_STORAGE_CONNECTION_STRING") or "").strip().strip('"').strip("'")
    secret_key = (os.getenv("AWS_OPEN_AI_KEY") or "").strip().strip('"').strip("'")
    region = os.getenv("REGION", "eu-central-1")
    chat_model = os.getenv("AWS_OPENAI_MODEL")
    embed_model = os.getenv("AWS_OPENAI_EMBEDDING_DEPLOYMENT")

    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    bedrock = session.client("bedrock-runtime")

    print(f"Testing Chat Model: {chat_model} in {region}")
    try:
        bedrock.invoke_model(
            modelId=chat_model,
            body='{"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}'
        )
        print("Chat Model: OK")
    except Exception as e:
        print(f"Chat Model ERROR: {e}")

    print(f"\nTesting Embed Model: {embed_model} in {region}")
    try:
        bedrock.invoke_model(
            modelId=embed_model,
            body='{"inputText": "hi"}'
        )
        print("Embed Model: OK")
    except Exception as e:
        print(f"Embed Model ERROR: {e}")

if __name__ == "__main__":
    test_models()
