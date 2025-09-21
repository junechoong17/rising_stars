import boto3
import json
import os
from datetime import datetime

# Initialize Bedrock Runtime client
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("ChatHistory")

def lambda_handler(event, context):
    try:
        # Handle CORS preflight request
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,POST",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization"
                }
            }

        # Parse body from API Gateway event
        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "Hello!")

        # Build Bedrock request
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": f"You are AI QnA Tutor, a friendly and helpful assistant that answers questions clearly and concisely.\n\nUser Question: {question}"}
                    ]
                }
            ],
            "inferenceConfig": {
                "max_new_tokens": 256,
                "temperature": 0.7
            }
        }

        # Call Bedrock
        response = bedrock.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        # Decode response
        result = json.loads(response["body"].read())
        answer = result["output"]["message"]["content"][0]["text"]

        # ✅ Save to DynamoDB
        timestamp = datetime.utcnow().isoformat()
        user_id = "abudhabi"  # temporary, can replace with real auth user ID later

        table.put_item(
            Item={
                "user_id": user_id,     # Partition key
                "timestamp": timestamp, # Sort key, now a String
                "question": question,
                "answer": answer
            }
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
                "Access-Control-Allow-Headers": "Content-Type,Authorization"
            },
            "body": json.dumps({"answer": answer})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
                "Access-Control-Allow-Headers": "Content-Type,Authorization"
            },
            "body": json.dumps({"error": str(e)})
        }
