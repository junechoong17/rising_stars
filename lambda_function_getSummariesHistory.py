import os
import boto3
from boto3.dynamodb.conditions import Key
import json

DDB_TABLE = os.environ.get("DDB_TABLE")
GSI_NAME = "userId-timestamp-index"

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DDB_TABLE)

def lambda_handler(event, context):
    user_id = event.get("queryStringParameters", {}).get("userId", "demo")

    response = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key("userId").eq(user_id),
        ScanIndexForward=False  # latest first
    )

    items = response.get("Items", [])
    print("DEBUG: items =", items)

    return {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
    "body": json.dumps({"items": items})  # wrap in an object
    }

