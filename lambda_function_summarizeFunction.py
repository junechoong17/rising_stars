# lambda_function.py
import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

S3_BUCKET = os.environ.get("S3_BUCKET")
DDB_TABLE = os.environ.get("DDB_TABLE")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID")
REGION = os.environ.get("AWS_REGION", "us-east-1")

s3 = boto3.client("s3", region_name=REGION)
dynamodb = boto3.client("dynamodb", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

def safe_json_load(s):
    try:
        return json.loads(s)
    except Exception:
        return s

def extract_text_from_bedrock_response(raw_text):
    try:
        parsed = json.loads(raw_text)
        if "output" in parsed:
            msg = parsed["output"].get("message", {})
            if "content" in msg and len (msg["content"])>0:
                return msg["content"][0].get("text", raw_text)
        return raw_text
    except Exception:
        return raw_text


def lambda_handler(event, context):
    try:
        body = event.get("body") or "{}"
        if isinstance(body, str):
            body = safe_json_load(body)

        text = body.get("text") or body.get("article") or ""
        target_age = body.get("age") or body.get("targetAge") or 12
        user_id = body.get("userId") or "anonymous"

        if not text or not text.strip():
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Request must include 'text' in body."}),
                "headers": {"Content-Type": "application/json"}
            }

        # 1) Save original to S3
        item_id = str(uuid.uuid4())
        s3_key = f"originals/{item_id}.txt"
        s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=text.encode("utf-8"), ContentType="text/plain")

        # 2) Build Bedrock prompt (tune this template as needed)
        prompt = f"""Summarize and simplify the following text for a {target_age}-year-old student.
Do:
- Provide a 1-sentence summary.
- Provide 3 simple bullet points explaining key ideas.
- Give a 1-sentence real-world analogy.
- Give one short exercise (1 question).
Text:
{text}
"""

        # 3) Call Bedrock InvokeModel
        payload = json.dumps({
            "messages": [
                {"role": "user", "content": [{"text" : prompt}]}
            ],
            "inferenceConfig": {
                "maxTokens": 800,
                "temperature": 0.2
            }
        })

        resp = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=payload
        )

        # resp['body'] is a StreamingBody. Read it fully.
        raw = resp["body"].read().decode("utf-8")
        simplified = extract_text_from_bedrock_response(raw)

        # 4) Store metadata + simplified text in DynamoDB
        now = datetime.now(timezone.utc).isoformat()
        ddb_item = {
            "summaries_id": {"S": item_id},
            "userId": {"S": user_id},
            "timestamp": {"S": now},
            "s3Key": {"S": s3_key},
            "simplified": {"S": simplified}
        }
        dynamodb.put_item(TableName=DDB_TABLE, Item=ddb_item)


        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"id": item_id, "simplified": simplified})
        }

    except ClientError as e:
        print("AWS ClientError:", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    except Exception as e:
        print("Exception:", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}