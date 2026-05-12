import boto3
import json
from datetime import datetime, timezone, timedelta

SGT = timezone(timedelta(hours=8))
S3_BUCKET_ENV="user-corrections"
DEFAULT_S3_PREFIX="agentic-crms"

class SavingAgent:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str ) -> None: 
        self.client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def save_chat_logs(self, messages):
        """
        Saves the entire current chat session to S3.
        This overwrites the same session file each time.
        """
        s3_key = f"{DEFAULT_S3_PREFIX}/logs/{datetime.now(SGT).isoformat()}.json"

        self.client.put_object(
            Bucket=S3_BUCKET_ENV,
            Key=s3_key,
            Body=json.dumps(messages, ensure_ascii=False, indent=2),
            ContentType="application/json",
        )

    def save_notes(self, content: str, title: str, type: str):
        """
        Saves the entire current chat session to S3.
        This overwrites the same session file each time.
        """
        s3_key = f"{DEFAULT_S3_PREFIX}/{type}/{title}_{datetime.now(SGT).isoformat()}.md"

        self.client.put_object(
            Bucket=S3_BUCKET_ENV,
            Key=s3_key,
            Body=content,
            ContentType="text/markdown",
        )