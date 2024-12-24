import json
import logging

import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb", region_name="eu-north-1")
table = dynamodb.Table("Tracks")

def lambda_handler(event, context):
    try:
        track_id = event["pathParameters"]["id"]

        # Delete the item
        table.delete_item(
            Key={"id": track_id},
            ReturnValues="ALL_OLD"
        )

        # Always return success for delete
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Track deleted"})
        }

    except KeyError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing path parameter: {str(e)}"})
        }
    except ClientError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": e.response['Error']['Message']})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }