import json
import os
import boto3


S3_BUCKET = os.environ.get("S3_BUCKET")
s3 = boto3.client("s3")

def lambda_handler(event, context):
    s3_key = event.get("queryStringParameters", {}).get("s3Key")
    if not s3_key:
        return {"statusCode": 400, "body": "Missing s3Key parameter"}

    
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': S3_BUCKET, 'Key': s3_key},
        ExpiresIn=600  
    )
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": url
    }
