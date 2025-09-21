import boto3
from decimal import Decimal
from datetime import datetime
import json

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("LearningProgress")

def update_progress(user_id, topic_id, completion_value):
    """
    Updates or creates progress for a user-topic pair.
    completion_value = integer 0–100
    """
    response = table.update_item(
        Key={
            "UserID": user_id,
            "TopicID": topic_id
        },
        UpdateExpression="SET completion = :completion, lastUpdated = :ts",
        ExpressionAttributeValues={
            ":completion": Decimal(completion_value),
            ":ts": datetime.utcnow().isoformat()
        },
        ReturnValues="ALL_NEW"
    )
    return response["Attributes"]

def get_user_progress(user_id):
    """
    Fetch all progress records for a given user.
    """
    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("UserID").eq(user_id)
    )
    return response["Items"]

# Test run
if __name__ == "__main__":
    # Update sample progress
    update_progress("student123", "math101", 50)
    update_progress("student123", "science101", 75)
    update_progress("student123", "history101", 40)

    # Query dashboard view
    progress = get_user_progress("student123")
    print("📊 Student Progress Dashboard:")
    for record in progress:
        print(json.dumps(record, indent=4, default=str))


