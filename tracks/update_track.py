import boto3
import json

from botocore.exceptions import ClientError

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("Tracks")

def lambda_handler(event, context):
    try:
        track_id = event["pathParameters"]["id"]
        body = json.loads(event["body"])
        name = body.get("name")
        artist = body.get("artist")

        # Update item in DynamoDB
        response = table.update_item(
            Key={"id": track_id},
            UpdateExpression="SET #n = :name, artist = :artist",
            ExpressionAttributeNames={"#n": "name"},
            ExpressionAttributeValues={":name": name, ":artist": artist},
            ReturnValues="UPDATED_NEW"
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Track updated", "updatedAttributes": response["Attributes"]})
        }

    except KeyError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing key: {str(e)}"})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }