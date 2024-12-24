import os

import boto3
import json
from botocore.exceptions import ClientError
from utils.cors_utils import build_response  # Import from your Lambda Layer

TABLE_NAME = os.environ['DYNAMODB_TABLE']
BUCKET_NAME = os.environ['BUCKET_NAME']

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # Scan all items in the DynamoDB table
        response = table.scan()
        items = response.get("Items", [])

        # Generate pre-signed URLs for each track
        for item in items:
            if 's3Url' not in item:
                continue
            s3_key = item['s3Url'].split(f"s3://{BUCKET_NAME}/")[-1]
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': item['s3Key']},
                ExpiresIn=3600  # URL expires in 1 hour
            )
            item['presignedUrl'] = presigned_url  # Add pre-signed URL to response

        return build_response(200, json.dumps({"tracks": items}))

    except ClientError as e:
        return build_response(500, json.dumps({"error": e.response['Error']['Message']}))

    except Exception as e:
        return build_response(500, json.dumps({"error": str(e)}))